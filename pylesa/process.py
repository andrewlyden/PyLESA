"""Run jobs in separate process"""
from multiprocessing import Process, Queue
import logging
from tqdm import tqdm
from typing import Callable, Dict, List, Any

LOG = logging.getLogger(__name__)

SENTINEL = "STOP_JOB"

class OutputProcess:
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
        # Start process
        self._process = Process(target=self._run_job, args=(func, self._queue))
        self._process.start()
    
    def submit(self, args: List[Any]):
        self._queue.put(args)

    def stop(self):
        if self._process:
            self._queue.put(SENTINEL)
            self._process.join()

    def cancel(self):
        self._queue.empty()
        self.stop()