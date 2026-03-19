import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_name": getattr(record, "agent_name", None),
            "action": getattr(record, "action", record.getMessage()),
            "confidence_score": getattr(record, "confidence_score", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "status": getattr(record, "status", record.levelname.lower()),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("svos")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "svos.log"

    formatter = JsonFormatter()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    return logger


logger = _build_logger()


def log_decision(
    agent: str,
    action: str,
    confidence: float | None,
    result: str,
    duration_ms: float | None = None,
):
    status = result if result in {"success", "failure", "escalated"} else "success"
    logger.info(
        f"decision:{action}",
        extra={
            "agent_name": agent,
            "action": action,
            "confidence_score": confidence,
            "duration_ms": duration_ms,
            "status": status,
        },
    )
