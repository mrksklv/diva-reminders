# Diva Reminders 🌸

A simple bot that tracks posting consistency in your Telegram channel.

## Running the bot

1. Add the bot to the channel as an administrator (you may restrict any permissions)
2. Each notification recipient must open the bot and run `/start` once
3. Set the `.env` file up as shown in [`.env.example`](./.env.example)
4. Install the dependencies and start the bot:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
