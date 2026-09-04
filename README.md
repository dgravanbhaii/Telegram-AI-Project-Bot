# Telegram AI Bot (powered by Claude)

A simple Telegram bot that forwards user messages to Claude and replies with the
response. Keeps a short rolling conversation history per chat so the bot has
context, with `/reset` to clear it.

## 1. Create your Telegram bot

1. Open Telegram and message **@BotFather**.
2. Send `/newbot` and follow the prompts (pick a name and a username ending in `bot`).
3. BotFather will give you a token like `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.
   Keep it secret.

## 2. Get an Anthropic API key

Create one at https://console.anthropic.com/settings/keys.

## 3. Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `TELEGRAM_BOT_TOKEN` — from BotFather
- `ANTHROPIC_API_KEY` — from the Anthropic console

## 5. Run it

```bash
python bot.py
```

The bot uses long polling, so no public URL or webhook setup is needed — just
run it and message your bot on Telegram.

## Commands

- `/start` — greeting + instructions
- `/help` — same as `/start`
- `/reset` — clears the conversation history for that chat
- Any other text message is sent to Claude and the reply is sent back

## Notes / next steps

- **Memory is in-process only.** Conversation history lives in a Python dict
  and is lost on restart. For persistence, swap `chat_histories` for a
  SQLite table or Redis.
- **Deploying 24/7**: run this on a small VPS, a Fly.io/Railway app, or as a
  systemd service, with `python bot.py` kept alive (e.g. via `pm2`, `supervisord`,
  or a `systemd` unit) — long polling doesn't need an open inbound port.
- **Group chats**: by default Telegram only sends a bot all messages in a
  group if privacy mode is disabled (via BotFather → Bot Settings → Group
  Privacy) or if the bot is mentioned/replied to.
- **Rate limits / cost**: every message triggers an Anthropic API call —
  keep an eye on usage if you open the bot to many users.
- **Multi-user safety**: history is keyed by `chat_id`, so each Telegram
  chat gets its own independent conversation.
