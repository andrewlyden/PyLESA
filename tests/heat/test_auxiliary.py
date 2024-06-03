from pylesa.heat.auxiliary import Aux
import pytest

from pylesa.heat.enums import Fuel


class TestAuxiliary:
    @pytest.fixture
    def fuel_info(self):
        return {
            Fuel.GAS: {"energy_density": 20, "cost": 30},
            Fuel.WOOD: {"energy_density": 20, "cost": 71},
            Fuel.KEROSENE: {"energy_density": 43, "cost": 46},
        }

    def test_auxiliary(self, fuel_info):
        aux = Aux(Fuel.WOOD, 0.9, fuel_info)
        assert isinstance(aux, Aux)
        assert aux.cost == 71
        assert aux.energy_density == 20

    def test_electric(self, fuel_info):
        aux = Aux(Fuel.ELECTRIC, 0.9, fuel_info)
        assert aux.cost is None
        assert aux.energy_density is None

    def test_fuel_usage(self, fuel_info):
        aux = Aux(Fuel.WOOD, 0.9, fuel_info)
        assert aux.fuel_usage(10.0) == 10.0 / 0.9

    def test_bad_fuel_type(self, fuel_info):
        with pytest.raises(ValueError):
            Aux("bad", 0.9, fuel_info)

    def test_missing_fuel_info(self, fuel_info):
        fuel_info.pop(Fuel.KEROSENE)
        with pytest.raises(KeyError):
            Aux(Fuel.KEROSENE, 0.9, fuel_info)
