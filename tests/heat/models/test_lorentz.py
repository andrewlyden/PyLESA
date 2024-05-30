import numpy as np

from pylesa.heat.models import Lorentz, PerformanceModel


def arr(value: float):
    return np.array([value])


class TestLorentz:
    def test_cop_lorentz(self):
        cop, flow, ret, ambin, ambout = 2.8, 3.0, 70.0, 40.0, 12.0
        hp = Lorentz(2.8, flow, ret, ambin, ambout, 1000.0)
        assert isinstance(hp, PerformanceModel)
        assert hp.cop(flow, ret, ambin, ambout) == cop
        assert hp.cop(flow + 10.0, ret, ambin, ambout) < cop
        assert hp.cop(flow, ret - 2.0, ambin, ambout) > cop
        assert hp.cop(flow, ret, ambin + 2.0, ambout) > cop
        assert hp.cop(flow, ret, ambin, ambout - 2.0) < cop

    def test_hp_duty(self):
        cop, flow, ret, ambin, ambout = 2.8, 3.0, 70.0, 40.0, 12.0
        hp = Lorentz(cop, flow, ret, ambin, ambout, 1000.0)
        assert hp.duty(3.0) == 3.0
        assert hp.duty(5000.0) == 1000.0 * cop
