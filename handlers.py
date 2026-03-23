import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from gpt import transcribe_voice, classify_intent, ask_chatgpt, split_long_message
from todo import add_task, get_tasks, format_task_list

logger = logging.getLogger(__name__)

# Maximum Telegram voice file size we'll accept (24 MB)
MAX_VOICE_BYTES = 24 * 1024 * 1024


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Привет! Я голосовой бот-ассистент.\n\n"
        "Отправь мне голосовое сообщение — я распознаю его и:\n"
        "• Отвечу на вопрос через ChatGPT\n"
        "• Или сохраню задачу, если ты скажешь «запомни», «сделать», «запиши» и т.д.\n\n"
        "Команды:\n"
        "/tasks — показать список задач\n"
        "/start — это сообщение\n\n"
        "Можно также писать текстом — работает так же, как голос."
    )


async def handle_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info("User %d requested task list", user_id)
    try:
        tasks = await asyncio.to_thread(get_tasks)
        text = format_task_list(tasks)
    except Exception:
        logger.exception("Failed to load tasks for user %d", user_id)
        text = "Ошибка при загрузке задач. Попробуй ещё раз."
    await update.effective_message.reply_text(text)


async def _process_text(update: Update, text: str) -> None:
    """
    Core logic: classify intent and respond appropriately.
    Used by both voice and text message handlers.
    """
    message = update.effective_message
    user_id = update.effective_user.id

    intent = classify_intent(text)
    logger.info("User %d | intent=%s | text=%s", user_id, intent, text)

    if intent == "todo":
        try:
            task_id = await asyncio.to_thread(add_task, text)
            await message.reply_text(
                f"Задача #{task_id} сохранена:\n\n{text}"
            )
        except Exception:
            logger.exception("Failed to save task for user %d", user_id)
            await message.reply_text("Ошибка при сохранении задачи. Попробуй ещё раз.")
    else:
        try:
            answer = await ask_chatgpt(text)
            # Handle long answers: send in multiple messages if needed
            parts = split_long_message(answer)
            for part in parts:
                await message.reply_text(part)
        except Exception:
            logger.exception("ChatGPT call failed for user %d", user_id)
            await message.reply_text(
                "Ошибка при обращении к ChatGPT. Проверь API-ключ или попробуй позже."
            )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user_id = update.effective_user.id
    voice = message.voice

    logger.info(
        "Voice message from user %d: duration=%ds, size=%d bytes",
        user_id,
        voice.duration,
        voice.file_size or 0,
    )

    # Check file size before downloading
    if voice.file_size and voice.file_size > MAX_VOICE_BYTES:
        await message.reply_text(
            "Голосовое сообщение слишком длинное (максимум ~24 МБ). "
            "Попробуй отправить более короткое."
        )
        return

    await message.reply_text("Распознаю речь...")

    # Download OGG file from Telegram
    try:
        tg_file = await context.bot.get_file(voice.file_id)
        ogg_bytes = bytes(await tg_file.download_as_bytearray())
    except Exception:
        logger.exception("Failed to download voice file from user %d", user_id)
        await message.reply_text("Не удалось скачать голосовое сообщение. Попробуй ещё раз.")
        return

    # Transcribe via Whisper
    try:
        text = await transcribe_voice(ogg_bytes)
    except ValueError as e:
        # File size error from transcribe_voice
        logger.warning("Voice file rejected for user %d: %s", user_id, e)
        await message.reply_text(str(e))
        return
    except Exception:
        logger.exception("Whisper transcription failed for user %d", user_id)
        await message.reply_text("Не удалось распознать речь. Попробуй говорить чётче.")
        return

    if not text:
        await message.reply_text("Речь не распознана. Попробуй говорить чётче и ближе к микрофону.")
        return

    await message.reply_text(f"Распознано: {text}")

    # Process the transcribed text
    await _process_text(update, text)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages (useful for testing without voice)."""
    message = update.effective_message
    text = message.text.strip() if message.text else ""

    if not text:
        return

    logger.info("Text message from user %d: %s", update.effective_user.id, text)
    await _process_text(update, text)


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unsupported message types (photos, stickers, etc.)."""
    await update.effective_message.reply_text(
        "Я понимаю только голосовые и текстовые сообщения. "
        "Отправь голосовое или напиши текстом."
    )
