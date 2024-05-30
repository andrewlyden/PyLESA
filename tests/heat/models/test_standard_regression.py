import numpy as np
import pandas as pd
import pytest

from pylesa.heat.models import StandardTestRegression, PerformanceModel


@pytest.fixture
def xarr():
    # ambient, flow
    return np.array([[0, 50.0], [10.0, 50.0], [0, 75.0], [10.0, 75.0]])


@pytest.fixture
def cosparr():
    return np.array([4.0, 3.0, 3.5, 2.5])


@pytest.fixture
def dutyarr():
    return np.array([1000.0, 1500.0, 2000.0, 2500.0])


@pytest.fixture
def hp(xarr, cosparr, dutyarr):
    return StandardTestRegression(xarr, cosparr, dutyarr)


class TestStandardTestRegression:

    def test_cop(self, hp):
        assert isinstance(hp, PerformanceModel)
        ambient = [1.0, 5.0]
        flow = [55.0, 60]
        cop = hp.cop(ambient, flow)
        assert cop.shape == (2,)
        assert 4.0 > cop[0] > 3.5
        assert 4.0 > cop[1] > 3.5
        assert cop[0] > cop[1]

    def test_duty(self, hp):
        ambient = [1.0, 5.0]
        flow = [55.0, 60]
        duty = hp.duty(ambient, flow)
        assert duty.shape == (2,)
        assert 1000.0 < duty[0] < 2000.0
        assert 1000.0 < duty[1] < 2000.0
        assert duty[1] > duty[0]

    def test_bad_shapes(self, xarr, cosparr, dutyarr):
        with pytest.raises(IndexError):
            StandardTestRegression(xarr[:-1, :], cosparr, dutyarr)

        with pytest.raises(IndexError):
            StandardTestRegression(xarr, cosparr[:-1], dutyarr)

        with pytest.raises(IndexError):
            StandardTestRegression(xarr, cosparr, dutyarr[:-1])

    def test_fit(self, hp):
        x = np.array([1.0, 3.0])
        x1 = np.array([10.0, 30.0])
        fit = hp._fit(x, x1)
        assert 1 == 1

    def test_train_with_pandas(self, hp, xarr, cosparr, dutyarr):
        ambient = [1.0, 5.0]
        flow = [55.0, 60]

        # train gets called on init
        hp2 = StandardTestRegression(
            pd.DataFrame(xarr), pd.DataFrame(cosparr), pd.DataFrame(dutyarr)
        )
        hp3 = StandardTestRegression(
            pd.DataFrame(xarr), pd.Series(cosparr), pd.Series(dutyarr)
        )

        # check results
        assert np.allclose(hp.cop(ambient, flow), hp2.cop(ambient, flow))
        assert np.allclose(hp2.cop(ambient, flow), hp3.cop(ambient, flow))
