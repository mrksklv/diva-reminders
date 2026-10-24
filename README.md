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
