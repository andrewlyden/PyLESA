import logging
import io
from pathlib import Path
import pytest
import time

from pylesa.mp.process import OutputProcess

LOG = logging.getLogger(__name__)


def task(filepath: str):
    filepath = Path(filepath).resolve()
    with open(filepath, "w") as f:
        f.write("test")
        LOG.info(f"Wrote: {filepath.stem}")

@pytest.fixture
def process():
    p = OutputProcess()
    p.start(task)
    yield p
    p.stop()

class TestOutputProcess:
    def test_run_job(self, process: OutputProcess, tmpdir):
        fpaths = [Path(tmpdir) / f"test_{idx}.txt" for idx in range(5)]
        for fpath in fpaths:
            process.submit([fpath])

        # Wait for files to be written
        time.sleep(2)

        for fpath in fpaths:
            assert Path(fpath).exists()

    def test_handle_task_error(self, process: OutputProcess):
        bad_path = "bad/path"
        with pytest.raises(SystemError):
            process.submit([bad_path])
            # Stop waits for jobs to finish and queue to be emptied
            process.stop()
        
        assert not process.is_alive()

class TestLogging:
    @pytest.fixture
    def stream_handler(self):
        # Add in string io object
        root = logging.getLogger()
        stream = io.StringIO()
        root.addHandler(logging.StreamHandler(stream=stream))
        yield stream

    @pytest.fixture
    def process_and_stream(self, stream_handler):
        """Setup process after setting up stream_handler"""
        p = OutputProcess()
        p.start(task)
        yield p, stream_handler
        p.stop()
    
    def test_logging(self, process_and_stream, tmpdir):
        process, stream = process_and_stream

        fpaths = [Path(tmpdir) / f"test_{idx}.txt" for idx in range(5)]
        for fpath in fpaths:
            process.submit([fpath])

        time.sleep(2)

        # Check log messages
        stream.seek(0)
        lines = stream.readlines()
        assert len(lines) == len(fpaths)
        for fpath in fpaths:
            assert f"Wrote: {fpath.stem}\n" in lines