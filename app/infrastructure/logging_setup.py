from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
import time as _time
from logging import Handler
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any
import socket
import shutil

from app.config import settings


_STANDARD_LOG_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


_LOGGING_INITIALIZED = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Respect settings.log_utc for timestamp timezone
        if bool(getattr(settings, "log_utc", True)):
            _dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        else:
            _dt = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone()

        payload: dict[str, Any] = {
            "time": _dt.isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno,
            "func": record.funcName,
            "process": record.process,
            "thread": record.thread,
        }
        # ELK-friendly additional fields
        payload["service"] = getattr(settings, "app_name", "app")
        payload["host"] = socket.gethostname()
        env_name = os.getenv("ENV") or os.getenv("ENVIRONMENT") or None
        if env_name:
            payload["environment"] = env_name
        # extras
        for k, v in record.__dict__.items():
            if k not in _STANDARD_LOG_KEYS and k not in payload:
                try:
                    json.dumps(v)  # ensure serializable
                    payload[k] = v
                except Exception:
                    payload[k] = str(v)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(payload, ensure_ascii=False)


def _apply_formatter_to_logger(logger_name: str, formatter: logging.Formatter) -> None:
    logger = logging.getLogger(logger_name)
    for h in logger.handlers:
        h.setFormatter(formatter)


def init_logging() -> None:
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Console: human-readable text; File: JSON (if enabled)
    text_formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Use UTC or localtime for console timestamps per settings
    if bool(getattr(settings, "log_utc", True)):
        text_formatter.converter = _time.gmtime  # type: ignore[attr-defined]
    else:
        text_formatter.converter = _time.localtime  # type: ignore[attr-defined]
    json_formatter: logging.Formatter = JsonFormatter()

    # Stream handler (console) — ensure exactly one
    stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)]
    if not stream_handlers:
        sh = logging.StreamHandler()
        sh.setLevel(level)
        sh.setFormatter(text_formatter)
        root.addHandler(sh)
    else:
        # Keep the first, standardize formatter, remove duplicates to avoid double logs
        primary = stream_handlers[0]
        primary.setFormatter(text_formatter)
        for h in stream_handlers[1:]:
            try:
                root.removeHandler(h)
            except Exception:
                pass

    # File handler (JSON)
    if settings.log_file_enabled:
        log_dir = Path(settings.log_dir)
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        log_path = log_dir / settings.log_file_name

        def is_same_file_handler(handler: Handler) -> bool:
            return (
                getattr(handler, "baseFilename", None) == os.fspath(log_path)
                and isinstance(handler, (RotatingFileHandler, TimedRotatingFileHandler))
            )

        if not any(is_same_file_handler(h) for h in root.handlers):
            if getattr(settings, "log_rotation", "size").lower() == "time":
                fh = TimedRotatingFileHandler(
                    filename=os.fspath(log_path),
                    when=getattr(settings, "log_when", "midnight"),
                    interval=int(getattr(settings, "log_interval", 1)),
                    backupCount=int(settings.log_backup_count),
                    encoding="utf-8",
                    utc=bool(getattr(settings, "log_utc", True)),
                )
                # Daily split into logs/YYYY-MM-DD/server.log on rollover
                if bool(getattr(settings, "log_daily_split", True)):
                    # Use simple date suffix to parse
                    fh.suffix = "%Y-%m-%d"

                    def _namer(default_name: str) -> str:  # e.g., logs/server.log.2025-08-11
                        return default_name

                    def _rotator(source: str, dest: str) -> None:
                        # Move rotated file into dated subdir
                        base_dir = Path(settings.log_dir)
                        date_suffix = Path(dest).name.split(".")[-1]
                        out_dir = base_dir / date_suffix
                        try:
                            out_dir.mkdir(parents=True, exist_ok=True)
                        except Exception:
                            pass
                        target = out_dir / Path(settings.log_file_name)
                        try:
                            shutil.move(source, os.fspath(target))
                        except Exception:
                            # Fallback: copy then remove
                            shutil.copy2(source, target)
                            try:
                                os.remove(source)
                            except Exception:
                                pass

                    fh.namer = _namer
                    fh.rotator = _rotator
            else:
                fh = RotatingFileHandler(
                    filename=os.fspath(log_path),
                    maxBytes=int(settings.log_max_bytes),
                    backupCount=int(settings.log_backup_count),
                    encoding="utf-8",
                )
            fh.setLevel(level)
            fh.setFormatter(json_formatter)
            root.addHandler(fh)
        else:
            for h in root.handlers:
                if is_same_file_handler(h):
                    h.setFormatter(json_formatter)

    # Align uvicorn formatters: console=text, file=json
    _apply_formatter_to_logger("uvicorn", text_formatter)
    _apply_formatter_to_logger("uvicorn.error", text_formatter)
    _apply_formatter_to_logger("uvicorn.access", text_formatter)

    _LOGGING_INITIALIZED = True


