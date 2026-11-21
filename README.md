# Diva Reminders 🌸

A small Python bot that tracks posting consistency in a Telegram channel.

## Run

1. Add the bot to the channel as an administrator.
2. Each notification recipient must open the bot and run `/start` once.
3. Copy `.env.example` to `.env` and fill in the bot token, channel, and subscribers.
4. Install the dependencies and start the bot:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The bot uses long polling, so keep the process running. It sends one notification
per post or album, and checks reminders at 22:00 and midnight in `TIMEZONE`.
State is stored in `STATE_FILE` (default: `.state.json`); preserve it across restarts.
`INITIAL_LAST_POST_AT` is used only when no saved state exists.

## `/emoji`

`/emoji` shows a button per basic color. Picking one sends the 10 closest emoji,
and 🔀 shuffles 10 random emoji that are generally that color. The shuffle pool
lives in `emoji_palette.json`: an emoji counts for a color when at least 50% of
its visible pixels (as rendered by Apple Color Emoji) are that color. To rebuild
it on macOS, run `pip install pillow emoji` and `python scripts/build_emoji_palette.py`.
