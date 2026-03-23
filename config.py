import os
import sys
from dotenv import load_dotenv

load_dotenv()

def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        print(f"ERROR: Required environment variable '{key}' is not set.")
        print("Copy .env.example to .env and fill in your API keys.")
        sys.exit(1)
    return value

TELEGRAM_BOT_TOKEN: str = _require_env("TELEGRAM_BOT_TOKEN")

# API keys — хотя бы один должен быть задан
DEEPSEEK_API_KEY: str = os.environ.get("OPENAI_API_KEY_depseak", "")
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY_openAi", "")

if not DEEPSEEK_API_KEY and not OPENAI_API_KEY:
    print("ERROR: Задайте хотя бы один ключ: OPENAI_API_KEY_depseak или OPENAI_API_KEY_openAi")
    sys.exit(1)

DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
DEEPSEEK_MODEL: str = "deepseek-chat"

TASKS_FILE: str = "tasks.json"
GPT_MODEL: str = "gpt-4o-mini"
WHISPER_MODEL: str = "whisper-1"

# Russian (and English) keywords that signal a TODO intent
TODO_KEYWORDS: list = [
    "запомни",
    "напомни",
    "добавь задачу",
    "добавь в список",
    "todo",
    "to do",
    "сделать",
    "нужно сделать",
    "не забудь",
    "поставь задачу",
    "запиши",
    "поставь в список",
    "внеси в список",
]
