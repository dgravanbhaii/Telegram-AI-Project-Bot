"""
Telegram AI Bot powered by Claude (Anthropic API).

Setup:
1. pip install -r requirements.txt
2. Copy .env.example to .env and fill in TELEGRAM_BOT_TOKEN and ANTHROPIC_API_KEY
3. python bot.py
"""

import logging
import os
from collections import defaultdict

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from anthropic import Anthropic, APIError

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful, friendly assistant chatting with someone on Telegram. "
    "Keep replies concise and conversational unless asked for more detail.",
)
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))  # user+assistant turns kept per chat

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Add it to your .env file.")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# In-memory per-chat conversation history: {chat_id: [{"role": ..., "content": ...}, ...]}
# NOTE: This resets whenever the bot process restarts. Swap in a database (e.g. SQLite/Redis)
# for persistence across restarts if you need it.
chat_histories: dict[int, list[dict]] = defaultdict(list)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    chat_histories.pop(chat_id, None)
    await update.message.reply_text(
        "Hi! I'm an AI assistant powered by Claude. Just send me a message and I'll respond.\n\n"
        "Commands:\n"
        "/reset — clear our conversation history\n"
        "/help — show this message again"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    chat_histories.pop(chat_id, None)
    await update.message.reply_text("Conversation history cleared. Fresh start!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if not user_text:
        return

    history = chat_histories[chat_id]
    history.append({"role": "user", "content": user_text})

    # Trim history to avoid unbounded growth / token bloat
    if len(history) > MAX_HISTORY_MESSAGES:
        history[:] = history[-MAX_HISTORY_MESSAGES:]

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        reply_text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        if not reply_text:
            reply_text = "Sorry, I didn't get a response back — try rephrasing that?"

        history.append({"role": "assistant", "content": reply_text})

    except APIError as e:
        logger.exception("Anthropic API error")
        # Don't leave a dangling user turn with no reply in history
        history.pop()
        reply_text = f"Sorry, I hit an error talking to Claude: {e}"

    except Exception:
        logger.exception("Unexpected error")
        history.pop()
        reply_text = "Sorry, something went wrong on my end. Please try again."

    await update.message.reply_text(reply_text)


def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
