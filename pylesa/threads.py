"""Threads for running pylesa solver and outputs"""
import concurrent.futures
import logging
from tqdm import tqdm
from typing import Callable, Dict, List, Any

LOG = logging.getLogger(__name__)

def run_pool(func: Callable, args: Dict[str, List], desc="Jobs") -> Dict[str, Any]:
    # We can use a with statement to ensure threads are cleaned up promptly
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        jobs = {job_key: [func] + list(arg) for job_key, arg in args.items()}
        # Start the jobs marking the Futures with the job_key
        submitted = {executor.submit(*job): job_key for job_key, job in jobs.items()}
        out = {}
        for future in tqdm(concurrent.futures.as_completed(submitted), desc=desc, total=len(list(jobs.keys()))):
            job_key = submitted[future]
            try:
                out[job_key] = future.result()
            except Exception as exc:
                LOG.error(f"Job {job_key} generated an exception: {exc}")
                raise exc
            else:
                LOG.info(f"Job {job_key} completed successfully")
        return out