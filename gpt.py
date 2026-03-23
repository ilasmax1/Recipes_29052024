import logging
import tempfile
from pathlib import Path

from openai import AsyncOpenAI

from config import DEEPSEEK_API_KEY, GPT_MODEL, WHISPER_MODEL, TODO_KEYWORDS

logger = logging.getLogger(__name__)

# Single shared client instance (connection pooling)
_client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

# Whisper file size limit: 25 MB
WHISPER_MAX_BYTES = 24 * 1024 * 1024

# Telegram message character limit
TG_MESSAGE_LIMIT = 4096


async def transcribe_voice(ogg_bytes: bytes) -> str:
    """
    Send raw OGG bytes to OpenAI Whisper API.
    Returns transcribed text string.

    Bug prevention:
    - tempfile MUST have .ogg suffix so OpenAI SDK can infer MIME type
    - language="ru" improves accuracy and reduces hallucinations on Russian speech
    """
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
            response = await _client.audio.transcriptions.create(
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


async def ask_chatgpt(question: str) -> str:
    """
    Send a question to DeepSeek and return the answer.
    """
    logger.info("DeepSeek question: %s", question)

    response = await _client.chat.completions.create(
        model=GPT_MODEL,
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

    answer = response.choices[0].message.content.strip()
    logger.info("DeepSeek answer (%d chars)", len(answer))
    return answer


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
        # Try to split at a newline before the limit
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks
