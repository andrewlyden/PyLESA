import numpy as np
import pytest

from pylesa.heat.models import PerformanceArray, PerformanceValue


@pytest.fixture
def cop():
    return np.array([3.0, 2.9, 2.8])


@pytest.fixture
def duty():
    return np.array([1000.0, 900.0, 800.0])


class TestPerformanceArray:
    def test_constructor(self, cop, duty):
        arr = PerformanceArray(cop, duty)
        assert isinstance(arr, PerformanceArray)
        assert np.allclose(cop, arr.cop)
        assert np.allclose(duty, arr.duty)

    def test_index_access(self, cop, duty):
        arr = PerformanceArray(cop, duty)
        assert isinstance(arr[1], PerformanceValue)
        assert arr[1].cop == 2.9
        assert arr[2].duty == 800.0

    def test_itter(self, cop, duty):
        arr = PerformanceArray(cop, duty)
        data = np.array([cop, duty])
        for idx, pv in enumerate(arr):
            assert np.allclose(data[:, idx], np.array([pv.cop, pv.duty]))

    def test_shape_mismatch(self, cop, duty):
        with pytest.raises(IndexError):
            PerformanceArray(cop, duty[:-1])

    def test_multi_dimensions(self, cop, duty):
        with pytest.raises(IndexError):
            PerformanceArray(np.array([cop, cop]), np.array([duty, duty]))
