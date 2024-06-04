from pathlib import Path
import pytest

from pylesa.process import OutputProcess


def task(filepath: str):
    with open(filepath, "w") as f:
        f.write("test")

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
        # Stop waits for jobs to finish and queue to be emptied
        process.stop()
        
        for fpath in fpaths:
            assert Path(fpath).exists()
        
        assert not process.is_alive()

    def test_handle_task_error(self, process: OutputProcess):
        bad_path = "bad/path"
        process.submit([bad_path])
        # Stop waits for jobs to finish and queue to be emptied
        process.stop()
        
        assert not process.is_alive()