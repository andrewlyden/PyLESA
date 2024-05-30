"""Constants used throughout the heat sub-package"""

from enum import Enum

ABS_ZERO = 273.15


class HP(Enum):
    ASHP = "ASHP"
    GSHP = "GSHP"
    WSHP = "WSHP"
