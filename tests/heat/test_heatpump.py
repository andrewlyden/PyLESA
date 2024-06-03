import numpy as np
import pandas as pd
import pytest

from pylesa.constants import ANNUAL_HOURS
from pylesa.heat.models import ModelName, HP, Simple, GenericRegression, StandardTestRegression, Lorentz, PerformanceArray, DataInput, PerformanceValue
from pylesa.heat.heatpump import HeatPump, HpDemand

from .models.test_standard_regression import xarr, cosparr, dutyarr


@pytest.fixture
def basic_kwargs():
    """Arguments needed for all heatpumps"""
    return {
        "hp_type": HP.ASHP,
        "capacity": 1000.,
        "ambient_delta_t": 2.,
        "minimum_runtime": 10.,
        "minimum_output": 20.,
        "data_input": DataInput.INTEGRATED,
        "flow_temp_source": pd.Series(np.full((ANNUAL_HOURS,), 60.)),
        "return_temp": pd.Series(np.full((ANNUAL_HOURS,), 30.)),
        "hp_ambient_temp": pd.DataFrame.from_dict(
            {
                "air_temperature": np.full((ANNUAL_HOURS,), 8.),
                "water_temperature": np.full((ANNUAL_HOURS,), 8.),
            }
        ),
    }

class TestHeatPump:
    def test_bad_model(self, basic_kwargs):
        with pytest.raises(KeyError):
            HeatPump(modelling_approach="bad", **basic_kwargs)

class TestSimple:
    @pytest.fixture
    def cop(self):
        return 2.8
    
    @pytest.fixture
    def model(self):
        return ModelName.SIMPLE
    
    @pytest.fixture
    def hp(self, basic_kwargs, model, cop):
        return HeatPump(modelling_approach=model, simple_cop=cop, **basic_kwargs)

    def test_model(self, hp):
        assert isinstance(hp, HeatPump)
        assert isinstance(hp.model, Simple)

    def test_performance(self, hp):
        performance = hp.performance()
        assert isinstance(performance, PerformanceArray)
        assert performance.cop.shape == (ANNUAL_HOURS,)
        assert performance.duty.shape == (ANNUAL_HOURS,)

    def test_missing_props(self, basic_kwargs, model):
        with pytest.raises(ValueError):
            # simple_cop is missing
            HeatPump(modelling_approach=model,  **basic_kwargs)

    @pytest.mark.parametrize("setter", ["flow_temp_source", "return_temp", "hp_ambient_temp"])
    def test_bad_length_data(self, hp, setter):
        short_data = np.ones((10,))
        with pytest.raises(ValueError):
            exec(f"hp.{setter} = short_data")

    def test_properties(self, hp, basic_kwargs):
        assert hp.minimum_runtime == basic_kwargs["minimum_runtime"]
        assert hp.minimum_output == basic_kwargs["minimum_output"]
        assert hp.data_input == basic_kwargs["data_input"]

class TestGeneric:
    @pytest.fixture
    def model(self):
        return ModelName.GENERIC
    
    @pytest.fixture
    def hp(self, basic_kwargs, model):
        return HeatPump(modelling_approach=model, **basic_kwargs)

    def test_model(self, hp):
        assert isinstance(hp, HeatPump)
        assert isinstance(hp.model, GenericRegression)

    def test_performance(self, hp):
        performance = hp.performance()
        assert isinstance(performance, PerformanceArray)
        assert performance.cop.shape == (ANNUAL_HOURS,)
        assert performance.duty.shape == (ANNUAL_HOURS,)

    def test_missing_props(self, basic_kwargs, model):
        basic_kwargs.pop("hp_type")
        with pytest.raises(TypeError):
            # hp_type is missing
            HeatPump(modelling_approach=model,  **basic_kwargs)

class TestStandard:
    @pytest.fixture
    def model(self):
        return ModelName.STANDARD
    
    @pytest.fixture
    def standard_inputs(self, xarr, cosparr, dutyarr):
        return {
            "data_x": xarr,
            "data_COSP": cosparr,
            "data_duty": dutyarr
        }
    
    @pytest.fixture
    def hp(self, basic_kwargs, model, standard_inputs):
        return HeatPump(modelling_approach=model, standard_inputs=standard_inputs, **basic_kwargs)

    def test_model(self, hp):
        assert isinstance(hp, HeatPump)
        assert isinstance(hp.model, StandardTestRegression)

    @pytest.mark.parametrize("data", [DataInput.INTEGRATED, DataInput.PEAK])
    def test_performance(self, basic_kwargs, model, standard_inputs, data):
        basic_kwargs["data_input"] = data
        hp = HeatPump(modelling_approach=model, standard_inputs=standard_inputs, **basic_kwargs)
        performance = hp.performance()
        assert isinstance(performance, PerformanceArray)
        assert performance.cop.shape == (ANNUAL_HOURS,)
        assert performance.duty.shape == (ANNUAL_HOURS,)
    
    @pytest.mark.parametrize("hp_type", [HP.GSHP, HP.WSHP])
    def test_performance_non_ashp(self, hp, hp_type):
        hp.hp_type = hp_type
        hp.data_input = DataInput.PEAK
        with pytest.raises(ValueError):
            hp.performance()

    def test_missing_props(self, basic_kwargs, model, standard_inputs):
        with pytest.raises(ValueError):
            # missing standard_inputs
            HeatPump(modelling_approach=model,  **basic_kwargs)

        with pytest.raises(TypeError):
            basic_kwargs.pop("data_input")
            HeatPump(modelling_approach=model,  standard_inputs=standard_inputs, **basic_kwargs)

class TestLorentz:
    @pytest.fixture
    def model(self):
        return ModelName.LORENTZ
    
    @pytest.fixture
    def lorentz_inputs(self, xarr, cosparr, dutyarr):
        return {
            "cop": 2.8,
            "flow_temp_spec": 70.,
            "return_temp_spec": 40.,
            "temp_ambient_in_spec": 12.,
            "temp_ambient_out_spec": 10.,
            "elec_capacity": 1000.
        }
    
    @pytest.fixture
    def hp(self, basic_kwargs, model, lorentz_inputs):
        return HeatPump(modelling_approach=model, lorentz_inputs=lorentz_inputs, **basic_kwargs)

    def test_model(self, hp):
        assert isinstance(hp, HeatPump)
        assert isinstance(hp.model, Lorentz)

    def test_performance(self, hp):
        performance = hp.performance()
        assert isinstance(performance, PerformanceArray)
        assert performance.cop.shape == (ANNUAL_HOURS,)
        assert performance.duty.shape == (ANNUAL_HOURS,)

    def test_missing_props(self, basic_kwargs, model):
        with pytest.raises(ValueError):
            # missing lorentz_inputs
            HeatPump(modelling_approach=model,  **basic_kwargs)

class TestHeatResource:
    def test_heat_resource(self):
        pass

class TestElecUsage:
    @pytest.fixture
    def hp(self, basic_kwargs):
        return HeatPump(modelling_approach=ModelName.SIMPLE, simple_cop=2.8, **basic_kwargs)

    @pytest.fixture
    def performance(self):
        return PerformanceValue(2.8, 1000.)

    def test_elec_usage(self, hp: HeatPump, performance):
        out = hp.elec_usage(10., performance)
        assert out == 10. / 2.8

    def test_zero_capacity(self, hp: HeatPump, performance):
        hp.capacity = 0.
        assert hp.elec_usage(10., performance) == 0.

class TestThermalOutput:
    @pytest.fixture
    def hp(self, basic_kwargs):
        return HeatPump(modelling_approach=ModelName.SIMPLE, simple_cop=2.8, **basic_kwargs)

    @pytest.fixture
    def performance(self):
        return PerformanceValue(2.8, 1000.)
    
    def test_thermal_output(self, hp: HeatPump, performance):
        out = hp.thermal_output(1., performance, 10.)
        assert isinstance(out, HpDemand)
        assert out.demand == 2.8
        assert out.elec == 1.

    def test_zero_capacity(self, hp: HeatPump, performance):
        hp.capacity = 0.
        out = hp.thermal_output(1., performance, 10.)
        assert out.demand == 0.
        assert out.elec == 0.