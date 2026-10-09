# Diva Reminders 🌸

A small [Telegram Serverless](https://core.telegram.org/bots/serverless) bot that
tracks post consistency in a Telegram channel.

## Configuration

Add two secrets under **Settings → Secrets and variables → Actions**:

| Secret | Value |
| --- | --- |
| `BOT_CONFIG` | Your settings as JSON matching `config.example.json` |
| `TGCLOUD_TOKEN` | BotFather → Serverless → CLI Access token (not the bot API token) |

Don't forget to add the bot as a channel administrator and message the bot from each account you re planning to put on subscription.

## Legacy deployment

The previous Python implementation is in `legacy/`. To run it, follow these steps:

1. Set the `.env` file up as shown in [`.env.example`](./.env.example)
2. Install the dependencies and start the bot:

```bash
cd legacy
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
python3 main.py
```