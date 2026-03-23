"""
Telegram Voice GPT Bot — Entry Point
=====================================
Принимает голосовые (и текстовые) сообщения.
Голос транскрибируется через OpenAI Whisper.
Текст классифицируется:
  • "запомни" / "сделать" / "запиши" и т.д. → сохраняется как задача
  • всё остальное → передаётся в ChatGPT, ответ отправляется пользователю

Команды:
  /start  — приветствие и инструкция
  /tasks  — список сохранённых задач

Запуск:
  1. cp .env.example .env
  2. Заполни TELEGRAM_BOT_TOKEN и OPENAI_API_KEY в .env
  3. pip install -r requirements.txt
  4. python bot.py
"""

import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from handlers import (
    handle_start,
    handle_tasks_command,
    handle_voice,
    handle_text,
    handle_unknown,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting Telegram Voice GPT Bot...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("tasks", handle_tasks_command))

    # Voice messages
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Plain text messages (also useful for testing without voice)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Unsupported content types (photos, stickers, documents, etc.)
    app.add_handler(MessageHandler(
        ~filters.VOICE & ~filters.TEXT & ~filters.COMMAND,
        handle_unknown,
    ))

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
