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
DEEPSEEK_API_KEY: str = _require_env("DEEPSEEK_API_KEY")

TASKS_FILE: str = "tasks.json"
GPT_MODEL: str = "deepseek-chat"
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
