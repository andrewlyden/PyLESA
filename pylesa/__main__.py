import logging
import typer

from .main import main

LOG = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        typer.run(main)
    except Exception as e:
        LOG.error(e, exc_info=True)
        raise e