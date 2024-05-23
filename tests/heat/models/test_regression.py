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

class TestCop:
    @pytest.mark.parametrize("hp,estimate", [("ashp", 2.98), ("gshp", 3.94), ("wshp", 3.94)])
    def test_hp_cop(self, hp, estimate, request):
        hp = request.getfixturevalue(hp)
        out = hp.cop(50, 10)
        assert isinstance(out, float)
        assert estimate == round(out, 2)

    @pytest.mark.parametrize("hp", ["ashp", "gshp", "wshp"])
    def test_flow_performance(self, hp, request):
        hp = request.getfixturevalue(hp)
        assert hp.cop(40, 10) > hp.cop(60, 10)

    @pytest.mark.parametrize("hp", ["ashp", "gshp", "wshp"])
    def test_ambient_performance(self, hp, request):
        hp = request.getfixturevalue(hp)
        assert hp.cop(60, 20) > hp.cop(60, 10)

    def test_gshp_vs_ashp(self, ashp, gshp):
        assert gshp.cop(60, 10) > ashp.cop(60, 10)

    def test_gshp_wshp_equal(self, gshp, wshp):
        flow = 50
        ambient = 10
        assert gshp.cop(flow, ambient) == wshp.cop(flow, ambient)

    def test_bad_pump_selection(self):
        with pytest.raises(KeyError):
            ashp = GenericRegression("BadType")
            ashp.cop(50, 10)

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