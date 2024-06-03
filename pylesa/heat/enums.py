from enum import Enum, EnumMeta
import logging

LOG = logging.getLogger(__name__)


class SingleTypeCheck(EnumMeta):

    def __contains__(cls, item):
        return item in cls.__members__.values()

    def from_value(cls, value):
        """Raises KeyError if value doesn't exist"""
        for item in cls:
            if item.value == value:
                return item

        # raise KeyError
        msg = f"Value {value} does not exist in Enum items {list(cls)}"
        LOG.error(msg)
        raise KeyError(msg)


class HP(str, Enum, metaclass=SingleTypeCheck):
    ASHP = "ASHP"
    GSHP = "GSHP"
    WSHP = "WSHP"


class ModelName(str, Enum, metaclass=SingleTypeCheck):
    SIMPLE = "SIMPLE"
    LORENTZ = "LORENTZ"
    GENERIC = "GENERIC REGRESSION"
    STANDARD = "STANDARD TEST REGRESSION"


class DataInput(str, Enum, metaclass=SingleTypeCheck):
    INTEGRATED = "INTEGRATED PERFORMANCE"
    PEAK = "PEAK PERFORMANCE"

class Fuel(str, Enum, metaclass=SingleTypeCheck):
    GAS = "GAS"
    WOOD = "WOOD CHIPS"
    KEROSENE = "KEROSENE"
    ELECTRIC = "ELECTRIC"