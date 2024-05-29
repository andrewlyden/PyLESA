import numpy as np
import pytest

from pylesa.heat.models import HP, GenericRegression

@pytest.fixture
def ashp():
    return GenericRegression(HP.ASHP)

@pytest.fixture
def gshp():
    return GenericRegression(HP.GSHP)

@pytest.fixture
def wshp():
    return GenericRegression(HP.WSHP)

def arr(value: float):
    return np.array([value])

class TestCop:
    @pytest.mark.parametrize("hp,estimate", [("ashp", 2.98), ("gshp", 3.94), ("wshp", 3.94)])
    def test_hp_cop(self, hp, estimate, request):
        hp = request.getfixturevalue(hp)
        out = hp.cop(arr(50), arr(10))
        assert isinstance(out, np.ndarray)
        assert estimate == round(out[0], 2)

    @pytest.mark.parametrize("hp", ["ashp", "gshp", "wshp"])
    def test_flow_performance(self, hp, request):
        hp = request.getfixturevalue(hp)
        assert hp.cop(arr(40), arr(10)) > hp.cop(arr(60), arr(10))

    @pytest.mark.parametrize("hp", ["ashp", "gshp", "wshp"])
    def test_ambient_performance(self, hp, request):
        hp = request.getfixturevalue(hp)
        assert hp.cop(arr(60), arr(20)) > hp.cop(arr(60), arr(10))

    def test_gshp_vs_ashp(self, ashp, gshp):
        assert gshp.cop(arr(60), arr(10)) > ashp.cop(arr(60), arr(10))

    def test_gshp_vs_ashp_arr(self, ashp, gshp):
        gshp_out = gshp.cop(np.array([30, 60]), np.array([10, 20]))
        ashp_out = ashp.cop(np.array([30, 60]), np.array([10, 20]))
        assert np.all(gshp_out > ashp_out)

    def test_gshp_wshp_equal(self, gshp, wshp):
        flow = arr(50)
        ambient = arr(10)
        assert gshp.cop(flow, ambient) == wshp.cop(flow, ambient)

    def test_bad_pump_selection(self):
        with pytest.raises(KeyError):
            ashp = GenericRegression("BadType")

class TestDuty:
    @pytest.mark.parametrize("hp,estimate", [("ashp", 7.9), ("gshp", 12.37), ("wshp", 12.37)])
    def test_hp_duty(self, hp, estimate, request):
        hp = request.getfixturevalue(hp)
        out = hp.duty(10)
        assert isinstance(out, float)
        assert estimate == round(out, 2)

    def test_gshp_vs_ashp(self, ashp, gshp):
        assert gshp.duty(10) > ashp.duty(10)
    
    def test_gshp_wshp_equal(self, gshp, wshp):
        ambient = 10
        assert gshp.duty(ambient) == wshp.duty(ambient)

    def test_bad_pump_selection(self):
        with pytest.raises(KeyError):
            ashp = GenericRegression("BadType")
            ashp.duty(10)