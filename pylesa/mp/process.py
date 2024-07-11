"""Run jobs in separate process"""

import logging.handlers
from multiprocessing import Process, Queue
import logging
from threading import Thread
from typing import Callable, List, Any

from .constants import SENTINEL, TIMEOUT
from .logging import setup_mp_logging
from ..constants import DEFAULT_LOGLEVEL

LOG = logging.getLogger(__name__)


class OutputProcess:
    """Run func on a separate process submitting jobs via a queue"""

    def __init__(self):
        self._job_queue = Queue()
        self._log_queue = Queue()
        self._process = None
        self._logger = None

    @staticmethod
    def _run_job(func: Callable, job_queue: Queue, log_queue: Queue):
        # setup logging to pass messages back to main process
        root_logger = logging.getLogger().root
        setup_mp_logging(root_logger.level, log_queue)
        # Run job loop
        try:
            while True:
                job = job_queue.get()
                if job == SENTINEL:
                    break
                func(*job)
        except Exception as e:
            LOG.error(e)
            raise e

    def start(self, func: Callable) -> None:
        # Ensure queues are empty
        self._job_queue.empty()
        self._log_queue.empty()
        # Create queue listener to forward messages to existing handlers
        self._logger = logging.handlers.QueueListener(
            self._log_queue, *logging.getLogger().handlers, respect_handler_level=True
        )
        self._logger.start()
        # Start process
        self._process = Process(
            target=self._run_job, args=(func, self._job_queue, self._log_queue)
        )
        self._process.start()

    def submit(self, args: List[Any]):
        self._job_queue.put(args)

    def stop(self, block=True, timeout=TIMEOUT):
        try:
            if self._process:
                self._job_queue.put(SENTINEL)
                if not block:
                    timeout = None

                # Wait for process to join
                if self.is_alive():
                    self._process.join(timeout=timeout)

                if self._process.exitcode != 0:
                    msg = f"Output process exited with non-zero exit code: {self._process.exitcode}"
                    LOG.error(msg)
                    raise SystemError(msg)
        finally:
            if self._process:
                self._process.close()
                self._job_queue.empty()
                self._process = None

            if self._logger:
                self._logger.stop()
                self._logger = None

    def cancel(self, block=True):
        self._job_queue.empty()
        self.stop(block)

    def is_alive(self):
        try:
            if self._process:
                return self._process.is_alive()
            else:
                return False
        except ValueError:
            return False
