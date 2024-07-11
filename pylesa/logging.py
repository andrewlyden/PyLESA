import enum
import logging
from pathlib import Path

from .constants import LOG_FILENAME, CONSOLE_LOG_FORMAT, FILE_LOG_FORMAT


class CustomFormatter(logging.Formatter):
    green = "\x1b[32;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = CONSOLE_LOG_FORMAT

    FORMATS = {
        logging.DEBUG: green + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging(logdir: str | Path, level: enum.Enum):
    """Sets up logging handlers, removes any existing handlers

    A FileHandler and a StreamHandler (console) are created.

    Args:
        logdir: path to directory to write log file
        level: Enum defining the logging level
    """
    root = logging.getLogger()
    root.setLevel(min(logging.INFO, level))
    root.handlers.clear()
    handlers = []

    # Log to a file on disk
    # Level always set at least to INFO
    file_handler = logging.FileHandler(Path(logdir).resolve() / LOG_FILENAME, "w+")
    file_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT))
    handlers.append(file_handler)

    # Log to the console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CustomFormatter())
    console_handler.setLevel(level)
    handlers.append(console_handler)

    # Set format on handlers and add them to the root
    for handler in handlers:
        root.addHandler(handler)
