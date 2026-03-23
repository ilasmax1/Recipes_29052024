import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from config import TASKS_FILE

logger = logging.getLogger(__name__)


def _load_tasks() -> list:
    path = Path(TASKS_FILE)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load tasks from %s: %s", TASKS_FILE, e)
        return []


def _save_tasks(tasks: list) -> None:
    # Write to temp file first, then replace atomically to prevent corruption
    dir_name = os.path.dirname(os.path.abspath(TASKS_FILE)) or "."
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=dir_name,
            delete=False,
            suffix=".tmp",
        ) as tmp:
            json.dump(tasks, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, TASKS_FILE)
    except OSError as e:
        logger.error("Failed to save tasks: %s", e)
        raise


def add_task(text: str) -> int:
    """Add a new task. Returns the new task ID."""
    tasks = _load_tasks()
    task_id = (tasks[-1]["id"] + 1) if tasks else 1
    tasks.append({
        "id": task_id,
        "text": text,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "done": False,
    })
    _save_tasks(tasks)
    logger.info("Task #%d added: %s", task_id, text)
    return task_id


def get_tasks() -> list:
    """Return all tasks."""
    return _load_tasks()


def format_task_list(tasks: list) -> str:
    """Format task list as a human-readable string."""
    if not tasks:
        return "Список задач пуст."
    lines = ["Твои задачи:\n"]
    for t in tasks:
        status = "✓" if t.get("done") else "•"
        lines.append(f"{status} [{t['id']}] {t['text']}")
    return "\n".join(lines)
