"""Run jobs in separate process"""
from multiprocessing import Process, Queue
import logging
import time
from typing import Callable, List, Any

LOG = logging.getLogger(__name__)

SENTINEL = "STOP_JOB"
TIMEOUT = 30.

class OutputProcess:
    """Run func on a separate process submitting jobs via a queue"""
    def __init__(self):
        self._queue = Queue()
        self._process = None

    def _run_job(self, func: Callable, queue: Queue):
        while True:
            job = queue.get()
            if job == SENTINEL:
                break
            func(*job)

    def start(self, func: Callable) -> None:
        # Ensure queue is empty
        self._queue.empty()
        # Start process
        self._process = Process(target=self._run_job, args=(func, self._queue))
        self._process.start()
    
    def submit(self, args: List[Any]):
        self._queue.put(args)

    def stop(self, block=True, timeout=TIMEOUT):
        if self._process:
            self._queue.put(SENTINEL)
            if not block:
                timeout = None
            self._process.join(timeout=timeout)
            self._process.close()
            self._queue.empty()

    def cancel(self, block=True):
        self._queue.empty()
        self.stop(block)
    
    def is_alive(self):
        try:
            return self._process.is_alive()
        except ValueError:
            return False