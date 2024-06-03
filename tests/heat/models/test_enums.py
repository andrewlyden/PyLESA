from enum import Enum
import pytest

from pylesa.heat.models.enums import SingleTypeCheck, HP, ModelName


class Dummy(str, Enum, metaclass=SingleTypeCheck):
    FIRST = "first"
    SECOND = "second"

class TestSingleTypeCheck:
    def test_contains(self):
        assert "first" in Dummy
        assert "second" in Dummy
        assert "third" not in Dummy
    
    def test_from_value(self):
        assert Dummy.from_value("first") == Dummy.FIRST
        assert Dummy.from_value("second") == Dummy.SECOND
        with pytest.raises(KeyError):
            Dummy.from_value("third")

class TestHP:
    def test_metaclass(self):
        assert isinstance(HP, SingleTypeCheck)

    @pytest.mark.parametrize("hp", ["ASHP", "GSHP", "WSHP"])
    def test_options(self, hp):
        assert hp in HP


class TestModelName:
    def test_metaclass(self):
        assert isinstance(ModelName, SingleTypeCheck)

    @pytest.mark.parametrize("model", ["Simple", "Lorentz", "Generic regression", "Standard test regression"])
    def test_options(self, model):
        assert model.upper() in ModelName