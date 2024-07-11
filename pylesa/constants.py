import logging

DEFAULT_LOGLEVEL = logging.WARNING
FILE_LOG_FORMAT = "%(asctime)s: %(levelname)s: %(message)s"
CONSOLE_LOG_FORMAT = "%(levelname)s: %(message)s"
LOG_FILENAME = "pylesa.log"

INDIR = "inputs"
OUTDIR = "outputs"
ANNUAL_HOURS = 8760