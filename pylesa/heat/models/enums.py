from enum import Enum, EnumMeta

class SingleTypeCheck(EnumMeta):  
    def __contains__(cls, item): 
        return item in cls.__members__.values()

class HP(str, Enum, metaclass=SingleTypeCheck):
    ASHP = "ASHP"
    GSHP = "GSHP"
    WSHP = "WSHP"

class ModelName(str, Enum, metaclass=SingleTypeCheck):
    SIMPLE = "Simple"
    LORENTZ = "Lorentz"
    GENERIC = "Generic regression"
    STANDARD = "Standard test regression"
