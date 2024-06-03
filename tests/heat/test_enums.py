from enum import Enum
import pytest

from pylesa.heat.enums import SingleTypeCheck, HP, ModelName, DataInput


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
    def test_hp_options(self, hp):
        assert hp in HP


class TestModelName:
    def test_metaclass(self):
        assert isinstance(ModelName, SingleTypeCheck)

    @pytest.mark.parametrize(
        "model", ["Simple", "Lorentz", "Generic regression", "Standard test regression"]
    )
    def test_model_options(self, model):
        assert model.upper() in ModelName


class TestDataInput:
    def test_metaclass(self):
        assert isinstance(DataInput, SingleTypeCheck)

    @pytest.mark.parametrize("data", ["INTEGRATED PERFORMANCE", "PEAK PERFORMANCE"])
    def test_data_options(self, data):
        assert data in DataInput
