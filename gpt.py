import logging
import tempfile
from pathlib import Path

from openai import AsyncOpenAI, APIConnectionError, APIStatusError

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    OPENAI_API_KEY, GPT_MODEL,
    WHISPER_MODEL, TODO_KEYWORDS,
)

logger = logging.getLogger(__name__)

# Whisper file size limit: 25 MB
WHISPER_MAX_BYTES = 24 * 1024 * 1024

# Telegram message character limit
TG_MESSAGE_LIMIT = 4096

# Клиент DeepSeek (приоритет — дешевле)
_deepseek_client: AsyncOpenAI | None = (
    AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    if DEEPSEEK_API_KEY else None
)

# Клиент OpenAI (резервный)
_openai_client: AsyncOpenAI | None = (
    AsyncOpenAI(api_key=OPENAI_API_KEY)
    if OPENAI_API_KEY else None
)


async def transcribe_voice(ogg_bytes: bytes) -> str:
    """
    Send raw OGG bytes to OpenAI Whisper API.
    Whisper доступен только у OpenAI — DeepSeek его не поддерживает.
    """
    if not _openai_client:
        raise RuntimeError(
            "Транскрипция голоса требует OPENAI_API_KEY_openAi. Ключ не задан."
        )

    if len(ogg_bytes) > WHISPER_MAX_BYTES:
        raise ValueError(
            f"Voice file too large: {len(ogg_bytes)} bytes (max {WHISPER_MAX_BYTES})"
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(ogg_bytes)
            tmp_path = Path(tmp.name)

        with tmp_path.open("rb") as audio_file:
            response = await _openai_client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=audio_file,
                language="ru",
            )

        text = response.text.strip()
        logger.info("Whisper transcription (%d chars): %s", len(text), text)
        return text
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


def classify_intent(text: str) -> str:
    """
    Classify message intent using keyword heuristic.
    Returns 'todo' or 'question'.
    """
    lower = text.lower()
    for keyword in TODO_KEYWORDS:
        if keyword in lower:
            logger.debug("Intent=todo matched keyword '%s' in: %s", keyword, text)
            return "todo"
    logger.debug("Intent=question for: %s", text)
    return "question"


async def _chat_complete(client: AsyncOpenAI, model: str, question: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты полезный ассистент. Отвечай на русском языке. "
                    "Давай краткие и точные ответы. "
                    "Если вопрос на английском — отвечай на английском."
                ),
            },
            {"role": "user", "content": question},
        ],
        max_tokens=1024,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


async def ask_chatgpt(question: str) -> str:
    """
    Отправляет вопрос в DeepSeek (приоритет) или OpenAI (резерв).
    Если DeepSeek недоступен — автоматически переключается на OpenAI.
    """
    logger.info("Question: %s", question)

    if _deepseek_client:
        try:
            answer = await _chat_complete(_deepseek_client, DEEPSEEK_MODEL, question)
            logger.info("DeepSeek answer (%d chars)", len(answer))
            return answer
        except (APIConnectionError, APIStatusError) as e:
            logger.warning("DeepSeek failed (%s), falling back to OpenAI", e)

    if _openai_client:
        answer = await _chat_complete(_openai_client, GPT_MODEL, question)
        logger.info("OpenAI answer (%d chars)", len(answer))
        return answer

    raise RuntimeError("Нет доступных AI-провайдеров. Проверьте ключи в .env.")


def split_long_message(text: str, limit: int = TG_MESSAGE_LIMIT) -> list:
    """
    Split a long message into chunks that fit within Telegram's character limit.
    Splits on newlines where possible to avoid cutting mid-sentence.
    """
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks
