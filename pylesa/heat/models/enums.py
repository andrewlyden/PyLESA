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
    SIMPLE = "Simple"
    LORENTZ = "Lorentz"
    GENERIC = "Generic regression"
    STANDARD = "Standard test regression"
