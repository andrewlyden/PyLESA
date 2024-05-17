import logging
from pathlib import Path

LOG = logging.getLogger(__name__)


def valid_fpath(path: str | Path) -> Path:
    try:
        path = Path(path).resolve()
        if not path.exists():
            msg = f"File {path} does not exist"
            LOG.error(msg)
            raise FileNotFoundError(msg)
    except TypeError:
        msg = (
            f"Cannot define filepath using type {type(path)}, must be str or Path"
        )
        LOG.error(msg)
        raise TypeError(msg)
    return path


def valid_dir(path: str | Path) -> Path:
    try:
        path = Path(path).resolve()
        if not path.exists():
            msg = f"Directory {path} does not exist"
            LOG.error(msg)
            raise FileNotFoundError(msg)
    except TypeError:
        msg = f"Cannot define directory using type {type(path)}, must be str or Path"
        LOG.error(msg)
        raise TypeError(msg)
    return path
