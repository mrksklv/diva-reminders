import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.types import LinkPreviewOptions, Message
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    channel_id: int
    channel_username: str
    channel_emoji: str
    streak_days: int
    subscriber_ids: tuple[int, ...]
    timezone: ZoneInfo
    state_file: Path
    initial_last_post_at: datetime | None

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        # load and ensure bot token
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN isn't defined in .env")

        # load and format username
        username = os.getenv("CHANNEL_USERNAME").strip()
        if not username.startswith("@"):
            username = f"@{username}"

        # load and format subscriber IDs
        subscriber_ids = tuple(
            int(value.strip())
            for value in os.getenv("SUBSCRIBER_IDS").split(",")
            if value.strip()
        )
        
        timezone = ZoneInfo(os.getenv("TIMEZONE"))  # load timezone

        # load initial post so it survives restarts
        initial_value = os.getenv("INITIAL_LAST_POST_AT", "").strip()
        initial_last_post_at = datetime.fromisoformat(initial_value) if initial_value else None
        if initial_last_post_at and initial_last_post_at.tzinfo is None:
            initial_last_post_at = initial_last_post_at.replace(tzinfo=timezone)

        # load channel emoji
        channel_emoji = os.getenv("CHANNEL_EMOJI", "").strip()

        # load the allowed number of days without a post
        streak_days = int(os.getenv("STREAK_DAYS", "7"))
        if streak_days < 1:
            raise RuntimeError("STREAK_DAYS must be greater than zero")

        return cls(
            bot_token=token,
            channel_id=int(os.environ["CHANNEL_ID"]),
            channel_username=username,
            subscriber_ids=subscriber_ids,
            timezone=timezone,
            state_file=Path(os.getenv("STATE_FILE", ".state.json")),
            initial_last_post_at=initial_last_post_at,
            channel_emoji=channel_emoji,
            streak_days=streak_days,
        )  # return all loaded configuration

# functions to check for reminders

def due_reminder(
    last_post_date: date,
    now: datetime,
    sent: dict[str, bool],
    streak_days: int,
) -> str | None:
    """Return the reminder due now based on calendar dates."""
    current_date = now.date()
    current_time = now.time().replace(tzinfo=None)

    if current_date >= last_post_date + timedelta(days=streak_days + 1):
        return None if sent.get("lost") else "lost"
    if (
        current_date == last_post_date + timedelta(days=streak_days)
        and current_time >= time(22, 0)
    ):  # at 22:00 on the final day, the final reminder is due
        return None if sent.get("final") else "final"
    if (
        current_date == last_post_date + timedelta(days=streak_days - 1)
        and current_time >= time(22, 0)
    ): # at 22:00 on the day before the final day, the close reminder is due
        return None if sent.get("close") else "close"
    return None

def next_reminder_check(now: datetime) -> datetime:
    """Return the next time to check for reminders."""
    # reminders can only become due at midnight or 22:00
    next_midnight = datetime.combine(
        now.date() + timedelta(days=1),
        time(0, 0),
        tzinfo=now.tzinfo,
    )
    next_ten_pm = datetime.combine(now.date(), time(22, 0), tzinfo=now.tzinfo)
    if next_ten_pm <= now:
        next_ten_pm += timedelta(days=1)

    return min(next_midnight, next_ten_pm)

# functions to format elapsed time

def russian_number(value: int, one: str, few: str, many: str) -> str:
    """Format a russian number with the correct word form for 1, 2-4, and 5+."""
    if value % 10 == 1 and value % 100 != 11:
        word = one
    elif value % 10 in (2, 3, 4) and value % 100 not in (12, 13, 14):
        word = few
    else:
        word = many
    return f"{value} {word}"

def format_elapsed(last_post_at: datetime, now: datetime) -> str:
    """Format elapsed time in days and hours."""
    seconds = max(0, int((now - last_post_at).total_seconds()))
    days, remainder = divmod(seconds, 86_400)
    hours = remainder // 3_600

    parts = []
    if days:
        parts.append(russian_number(days, "день", "дня", "дней"))
    if hours:
        parts.append(russian_number(hours, "час", "часа", "часов"))

    if not parts:
        return "меньше часа назад"
    return " и ".join(parts) + " назад"


class StateStore:
    """A simple JSON file-based state store for the bot."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = asyncio.Lock()
        self.data = self._load()

    def _empty_state(self) -> dict:
        """Create an empty state with the initial last post date."""
        initial = self.settings.initial_last_post_at
        return {
            "last_post_at": initial.isoformat() if initial else None,
            "sent": {"close": False, "final": False, "lost": False},
        }

    def _load(self) -> dict:
        """Load data from the state file, or return an empty state."""
        if not self.settings.state_file.exists():
            return self._empty_state()
        try:
            return json.loads(self.settings.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logging.exception("Couldn't load state file, starting with empty state")
            return self._empty_state()

    def _save(self) -> None:
        """Save data to the state file."""
        self.settings.state_file.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def last_post_at(self) -> datetime | None:
        """Return the last post date."""
        value = self.data.get("last_post_at")
        return datetime.fromisoformat(value) if value else None

    async def remember_post(self, post_at: datetime) -> None:
        """Add a post to storage, if it is newer than the last post."""
        local_post_at = post_at.astimezone(self.settings.timezone)
        async with self.lock:
            previous = self.last_post_at()
            if previous and local_post_at <= previous:
                return
            self.data = {
                "last_post_at": local_post_at.isoformat(),
                "sent": {"close": False, "final": False, "lost": False},
            }
            self._save()

    async def mark_sent(self, reminder: str) -> None:
        """Mark a reminder as sent."""
        async with self.lock:
            self.data.setdefault("sent", {})[reminder] = True
            self._save()

# text presets:
TEXT_PRESETS = {
    "new": "✨ в канале вышел новый <a href=\"{post_url}\">пост</a>!",
    "close": "🔥 ты близко! завтра — последний день, чтобы сохранить серию",
    "final": "⏰ ОСТАЛОСЬ 2 ЧАСА! опубликуй пост до полуночи",
    "lost": "💔 серия потеряна — постов не было {days}",

    "hello": "👋 привет! я слежу за постами в {channel_username}",
    "last": "последний пост вышел {elapsed}",
    "no_posts": "я ещё не видел постов после запуска",
}


async def run_bot() -> None:
    # load settings and storage
    settings = Settings.from_env()
    store = StateStore(settings)
    # init bot
    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    router = Router()
    # set up tasks for handling media albums
    album_tasks: dict[str, asyncio.Task] = {}
    album_first_message_ids: dict[str, int] = {}

    def new_post_text(message_id: int) -> str:
        """Add a link to the post without escaping the notification text."""
        username = settings.channel_username.removeprefix("@")
        post_url = f"https://t.me/{username}/{message_id}"
        return TEXT_PRESETS["new"].format(post_url=post_url)

    async def notify_subscribers(text: str) -> None:
        """Send a message with a footer attached to all subscribers."""
        footer = f"<b>{settings.channel_emoji} {settings.channel_username}</b>".strip()
        message = f"{text}\n\n{footer}"
        for subscriber_id in settings.subscriber_ids:
            try:
                await bot.send_message(
                    subscriber_id,
                    message,
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
            except TelegramAPIError:
                logging.exception("Error trying to notify %s", subscriber_id)

    async def notify_album(media_group_id: str) -> None:
        """Notify subscribers of a new album after a short delay, to avoid duplicate notifications."""
        try:
            await asyncio.sleep(1.5)
            await notify_subscribers(new_post_text(album_first_message_ids[media_group_id]))
        finally:
            album_tasks.pop(media_group_id, None)
            album_first_message_ids.pop(media_group_id, None)

    @router.message(CommandStart())  # user start command
    async def start(message: Message) -> None:
        # check last post date and format elapsed time
        last_post_at = store.last_post_at()
        if last_post_at:
            now = datetime.now(settings.timezone)
            elapsed = format_elapsed(last_post_at, now)
            status = TEXT_PRESETS["last"].format(elapsed=elapsed)
        else:
            status = TEXT_PRESETS["no_posts"]

        # answer message
        await message.answer(
            TEXT_PRESETS["hello"].format(channel_username=settings.channel_username)
            + "\n"
            + status
        )

    @router.channel_post()
    async def channel_post(message: Message) -> None:
        if message.chat.id != settings.channel_id:  # ignore messages from other channels
            return

        await store.remember_post(message.date) # remember the post date

        # wait for other media to come if the post is part of a media group
        if message.media_group_id:
            group_id = str(message.media_group_id)
            # keep the first element as the album link target
            album_first_message_ids[group_id] = min(
                album_first_message_ids.get(group_id, message.message_id),
                message.message_id,
            )
            if group_id not in album_tasks:
                album_tasks[group_id] = asyncio.create_task(notify_album(group_id))
            return

        await notify_subscribers(new_post_text(message.message_id))  # notify subscribers about a new post

    async def check_reminders() -> None:
        """Check for reminders and notify subscribers if any are due."""
        # get last post date
        last_post_at = store.last_post_at()
        if not last_post_at:
            return

        # get now date
        now = datetime.now(settings.timezone)

        # get due reminders
        reminder = due_reminder(
            last_post_at.astimezone(settings.timezone).date(),
            now,
            store.data.get("sent", {}),
            settings.streak_days,
        )

        if reminder:  # if there are some
            text = TEXT_PRESETS[reminder].format(
                days=russian_number(settings.streak_days, "день", "дня", "дней")
            )
            await notify_subscribers(text)
            await store.mark_sent(reminder)

    async def reminder_loop() -> None:
        """Loop to check for reminders at the appropriate times."""
        while True:
            try:
                # check once after startup in case the bot was offline at a deadline
                await check_reminders()

                now = datetime.now(settings.timezone)
                next_check = next_reminder_check(now)
                await asyncio.sleep((next_check - now).total_seconds())  # sleep until next check time

            # handle exceptions
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("Error while checking for reminders")
                await asyncio.sleep(60)

    # set up loops and routers
    dispatcher.include_router(router)
    reminder_task = asyncio.create_task(reminder_loop())
    try:
        # start polling for updates
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        # shut bot down gracefully
        reminder_task.cancel()
        for task in album_tasks.values():
            task.cancel()
        await asyncio.gather(reminder_task, *album_tasks.values(), return_exceptions=True)
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )  # set up logging to a standard info format
    asyncio.run(run_bot())
