import os
import logging
import queue
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

LOG_DIR = "/var/log/ft_wheel"
os.makedirs(LOG_DIR, exist_ok=True)

# Avoid double-initialization if module reloaded
_initialized = globals().get("_initialized", False)

if not _initialized:
    log_queue = queue.Queue(-1)

    info_path = os.path.join(LOG_DIR, "admin_info.log")
    error_path = os.path.join(LOG_DIR, "admin_error.log")

    file_handler_info = RotatingFileHandler(info_path, maxBytes=10 * 1024 * 1024, backupCount=3)
    file_handler_info.setLevel(logging.INFO)
    file_handler_info.addFilter(lambda record: record.levelno <= logging.INFO)
    file_handler_error = RotatingFileHandler(error_path, maxBytes=10 * 1024 * 1024, backupCount=3)
    file_handler_error.setLevel(logging.ERROR)
    file_handler_error.addFilter(lambda record: record.levelno >= logging.ERROR)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler_info.setFormatter(formatter)
    file_handler_error.setFormatter(formatter)

    _queue_listener = QueueListener(log_queue, file_handler_info, file_handler_error)
    _queue_listener.start()

    logger = logging.getLogger("admin")
    logger.setLevel(logging.INFO)
    logger.addHandler(QueueHandler(log_queue))

    _initialized = True
    globals()["_initialized"] = True

__all__ = ["logger"]
