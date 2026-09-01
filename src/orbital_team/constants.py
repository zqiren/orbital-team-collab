from __future__ import annotations

SCHEMA_VERSION = "1.0"
RUNTIME_VERSION = "1"
RUNTIME_DIR_NAME = "orbital-team"
RUNTIME_MARKER = ".runtime-marker.json"
RUNTIME_MAGIC = "orbital-team-file-runtime"
DEFAULT_LOCK_TIMEOUT = 10.0
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600

STORE_SCHEMAS = {
    "members.json": "memberStore",
    "tasks.json": "taskStore",
    "potential-tasks.json": "potentialTaskStore",
    "open-questions.json": "openQuestionStore",
}

