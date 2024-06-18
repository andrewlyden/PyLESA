import enum
import logging
import logging.handlers
from multiprocessing import Queue


def setup_mp_logging(level: enum.Enum, queue: Queue):
    """Sets up StreamHandler to write to queue"""
    root = logging.getLogger().root
    root.handlers.clear()
    root.setLevel(min(logging.INFO, level))

    # Log to the queue
    queue_handler = logging.handlers.QueueHandler(queue)
    root.addHandler(queue_handler)
