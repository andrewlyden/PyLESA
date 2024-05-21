import pytest

from pylesa.heat.constants import HP
from pylesa.heat.generic_regression import cop, duty


class TestCop:
    def test_ashp(self):
        out = cop(HP.ASHP, 50, 10)
        assert isinstance(out, float)
        assert out > 0

    def test_flow_performance(self):
        assert cop(HP.ASHP, 40, 10) > cop(HP.ASHP, 60, 10)
        assert cop(HP.GSHP, 40, 10) > cop(HP.GSHP, 60, 10)

    def test_ambient_performance(self):
        assert cop(HP.ASHP, 60, 20) > cop(HP.ASHP, 60, 10)
        assert cop(HP.GSHP, 60, 20) > cop(HP.GSHP, 60, 10)

    def test_gshp_vs_ashp(self):
        assert cop(HP.GSHP, 60, 10) > cop(HP.ASHP, 60, 10)

    def test_gshp_wshp_equal(self):
        flow = 50
        ambient = 10
        assert cop(HP.GSHP, flow, ambient) == cop(HP.WSHP, flow, ambient)

    def test_bad_pump_selection(self):
        with pytest.raises(KeyError):
            cop("BadPumpType", 50, 10)

class TestDuty:
    def test_ashp(self):
        out = duty(HP.ASHP, 20)
        assert isinstance(out, float)
        assert out > 0

    def test_gshp_vs_ashp(self):
        assert duty(HP.GSHP, 10) > duty(HP.ASHP, 10)
    
    def test_gshp_wshp_equal(self):
        ambient = 10
        assert duty(HP.GSHP, ambient) == duty(HP.WSHP, ambient)

    def test_bad_pump_selection(self):
        with pytest.raises(KeyError):
            duty("BadPumpType", 10)