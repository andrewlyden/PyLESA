import numpy as np
import pytest

from pylesa.heat.models import Lorentz, PerformanceModel

def arr(value: float):
    return np.array([value])

class TestLorentz:
    def test_cop_lorentz(self):
        cop, flow, ret, ambin, ambout = 2.8, 3., 70., 40., 12.
        hp = Lorentz(2.8, flow, ret, ambin, ambout, 1000.)
        assert isinstance(hp, PerformanceModel)
        assert hp.cop(flow, ret, ambin, ambout) == cop
        assert hp.cop(flow + 10., ret, ambin, ambout) < cop
        assert hp.cop(flow, ret - 2., ambin, ambout) > cop
        assert hp.cop(flow, ret, ambin + 2., ambout) > cop
        assert hp.cop(flow, ret, ambin, ambout - 2.) < cop

    def test_hp_duty(self):
        cop, flow, ret, ambin, ambout = 2.8, 3., 70., 40., 12.
        hp = Lorentz(cop, flow, ret, ambin, ambout, 1000.)
        assert hp.duty(3.) == 3.
        assert hp.duty(5000.) == 1000. * cop