from dataclasses import dataclass
import logging
import numpy as np
import pandas as pd
from typing import Callable

from .enums import HP, ModelName, DataInput
from .models import (
    Lorentz,
    StandardTestRegression,
    GenericRegression,
    PerformanceArray,
    PerformanceModel,
    PerformanceValue,
    Simple,
)
from ..constants import ANNUAL_HOURS
from ..environment import weather

LOG = logging.getLogger(__name__)


@dataclass
class HpDemand:
    demand: float
    elec: float


class HeatPump:
    def __init__(
        self,
        hp_type: HP,
        modelling_approach: ModelName,
        capacity: float,
        ambient_delta_t: float,
        minimum_runtime: float,
        minimum_output: float,
        data_input: DataInput,
        flow_temp_source: int | float | pd.Series | np.ndarray,
        return_temp: int | float | pd.Series | np.ndarray,
        hp_ambient_temp: pd.DataFrame,
        simple_cop: float = None,
        lorentz_inputs: dict = None,
        standard_inputs: dict = None,
    ):
        """heat pump class object

        Args:
            hp_type, type of heatpump, ASHP, WSHP, GSHP
            modelling_approach, selects performance model
            capacity, thermal capacity of heat pump
            ambient_delta_t, drop in ambient source temperature
                from inlet to outlet
            minimum_runtime, fixed or variable speed compressor
            data_input, type of data input, peak or integrated
            flow_temp, required temperatures out of HP
            return_temp, inlet temp to HP
            hp_ambient_temp, ambient conditions of heat source for whole year
            simple_cop, COP for simple model, default: None
            lorentz_inputs, default: None
            standard_inputs, default: None
        """
        self.hp_type = hp_type
        self.capacity = capacity
        self.ambient_delta_t = ambient_delta_t
        self.minimum_runtime = minimum_runtime
        self.minimum_output = minimum_output
        self.data_input = data_input
        self.flow_temp_source = flow_temp_source
        self.return_temp = return_temp
        self.hp_ambient_temp = hp_ambient_temp

        self.simple_cop = simple_cop
        self.lorentz_inputs = lorentz_inputs
        self.standard_inputs = standard_inputs

        self.model = modelling_approach

    @staticmethod
    def _check_full_year(func: Callable):
        def _full_year_data(
            self, data: int | float | np.ndarray | pd.DataFrame | pd.Series
        ):
            if isinstance(data, int) or isinstance(data, float):
                data = np.full((ANNUAL_HOURS,), data)
            if data.shape[0] != ANNUAL_HOURS:
                msg = f"Data {func.__name__} is not provided for {data.shape[0]} hours, not a full year of {ANNUAL_HOURS} hours"
                LOG.error(msg)
                raise ValueError(msg)
            func(self, data)

        return _full_year_data

    @property
    def flow_temp_source(self):
        return self._flow_temp_source

    @flow_temp_source.setter
    @_check_full_year
    def flow_temp_source(self, data: np.ndarray | pd.Series):
        self._flow_temp_source = data

    @property
    def return_temp(self):
        return self._return_temp

    @return_temp.setter
    @_check_full_year
    def return_temp(self, data: np.ndarray | pd.Series):
        self._return_temp = data

    @property
    def hp_ambient_temp(self):
        return self._hp_ambient_temp

    @hp_ambient_temp.setter
    @_check_full_year
    def hp_ambient_temp(self, data: np.ndarray | pd.DataFrame | pd.Series):
        self._hp_ambient_temp = data

    @property
    def hp_type(self) -> HP:
        return self._hp_type
    
    @hp_type.setter
    def hp_type(self, value: HP):
        if value not in HP:
            msg = f"Invalid heat pump type: {value}, must be one of {[_.value for _ in HP]}"
            LOG.error(msg)
            raise ValueError(msg)
        self._hp_type = value

    @property
    def data_input(self) -> HP:
        return self._data_input
    
    @data_input.setter
    def data_input(self, value: DataInput):
        if value not in DataInput:
            msg = f"Invalid data input type: {value}, must be one of {[_.value for _ in DataInput]}"
            LOG.error(msg)
            raise ValueError(msg)
        self._data_input = value

    @property
    def model(self) -> PerformanceModel:
        return self._model

    @model.setter
    def model(self, approach: ModelName):
        """Generate PerformanceModel from modelling approach"""
        match approach:
            case ModelName.SIMPLE:
                if self.simple_cop is None:
                    msg = f"Heat pump performance model ({Simple}) cannot be initiated with simple_cop=None"
                    LOG.error(msg)
                    raise ValueError(msg)
                self._model = Simple(self.simple_cop, self.capacity)

            case ModelName.LORENTZ:
                if self.lorentz_inputs is None:
                    msg = f"Heat pump performance model ({Lorentz}) cannot be initiated with lorentz_inputs=None"
                    LOG.error(msg)
                    raise ValueError(msg)
                self._model = Lorentz(
                    self.lorentz_inputs["cop"],
                    self.lorentz_inputs["flow_temp_spec"],
                    self.lorentz_inputs["return_temp_spec"],
                    self.lorentz_inputs["temp_ambient_in_spec"],
                    self.lorentz_inputs["temp_ambient_out_spec"],
                    self.lorentz_inputs["elec_capacity"],
                )

            case ModelName.GENERIC:
                self._model = GenericRegression(self.hp_type)

            case ModelName.STANDARD:
                if self.standard_inputs is None:
                    msg = f"Heat pump performance model ({StandardTestRegression}) cannot be initiated with standard_inputs=None"
                    LOG.error(msg)
                    raise ValueError(msg)
                self._model = StandardTestRegression(
                    self.standard_inputs["data_x"],
                    self.standard_inputs["data_COSP"],
                    self.standard_inputs["data_duty"],
                )

            case _:
                msg = f"Performance model {approach} is not valid"
                LOG.error(msg)
                raise KeyError(msg)

    def heat_resource(self) -> pd.DataFrame:
        """accessing the heat resource

        takes the hp resource from the weather class

        Returns:
            dataframe, ambient temperature for heat source of heat pump
        
        Raises:
            ValueError if heat pump type is invalid
        """
        HP_resource = weather.Weather(
            air_temperature=self.hp_ambient_temp["air_temperature"],
            water_temperature=self.hp_ambient_temp["water_temperature"],
        ).heatpump()

        # self.hp_type has already been validated
        if self.hp_type == HP.ASHP:
            HP_resource = HP_resource.rename(
                columns={"air_temperature": "ambient_temp"}
            )
            return HP_resource[["ambient_temp"]]
        else:
            HP_resource = HP_resource.rename(
                columns={"water_temperature": "ambient_temp"}
            )
            return HP_resource[["ambient_temp"]]

    def performance(self) -> PerformanceArray:
        """performance over year of heat pump

        Returns:
            PerformanceArray defining cop and duty for each hour timestep in year
        """
        if self.capacity == 0:
            # TODO: change mpc to be clearer about how it uses cop and duty
            # cop needs to be low to not break the mpc solver
            # duty being zero means it won't choose it anyway
            cop = np.full((ANNUAL_HOURS,), 0.5)
            duty = np.zeros((ANNUAL_HOURS,))
            return PerformanceArray(cop, duty)

        ambient_temp = self.heat_resource()["ambient_temp"]

        duty_x = self.capacity

        match self.model:
            case Simple():
                return PerformanceArray(
                    np.full((ANNUAL_HOURS,), self.model.cop()),
                    np.full((ANNUAL_HOURS,), self.model.duty()),
                )

            case Lorentz():
                return PerformanceArray(
                    self.model.cop(
                        self.flow_temp_source.values,
                        self.return_temp.values,
                        ambient_temp.values,
                        ambient_temp.values - self.ambient_delta_t,
                    ),
                    np.full((ANNUAL_HOURS,), self.model.duty(self.capacity)),
                )

            case GenericRegression():
                return PerformanceArray(
                    self.model.cop(self.flow_temp_source.values, ambient_temp.values),
                    np.full((ANNUAL_HOURS,), duty_x),
                )

            case StandardTestRegression():
                cop = self.model.cop(ambient_temp.values, self.flow_temp_source.values)

                # 15% reduction in performance if
                # data not done to standards
                factor = np.ones(ambient_temp.shape)
                match self.data_input:
                    case DataInput.INTEGRATED:
                        factor = 1.0
                    case DataInput.PEAK:
                        if self.hp_type == HP.ASHP:
                            factor[ambient_temp <= 5.0] = 0.9
                        else:
                            msg = f"Peak performance option not available for {self.hp_type}"
                            LOG.error(msg)
                            raise ValueError(msg)
                    case _:
                        msg = (
                            f"{self.data_input} is not valid for {self.model.__class__}"
                        )
                        LOG.error(msg)
                        raise ValueError(msg)

                return PerformanceArray(
                    cop * factor, self.model.duty(ambient_temp, self.flow_temp_source)
                )

            case _:
                msg = f"Performance of {self.model} cannot be calculated"
                LOG.error(msg)
                raise ValueError(msg)

    def elec_usage(self, demand: float, hp_performance: PerformanceValue) -> float:
        """electricity usage of hp for timestep given a thermal demand

        Calculates the electrical usage of the heat pump given a heat demand.

        Args:
            demand, thermal demand to be met by heat pump
            hp_performance, PerformanceValue at specific timestep

        Returns:
            Electricity usage
        """
        if self.capacity == 0:
            return 0.0
        max_elec_usage = demand / hp_performance.cop
        max_elec_cap = hp_performance.duty / hp_performance.cop
        return min(max_elec_usage, max_elec_cap)

    def thermal_output(
        self, elec_supply: float, hp_performance: PerformanceValue, heat_demand: float
    ) -> HpDemand:
        """thermal output from a given electricity supply

        Args:
            elec_supply, electricity supply used by heat pump
            hp_performance, PerformanceValue at specific timestep
            heat_demand, heat demand to be met at timestep

        Returns:
            HpDemand object defining heat demand met by hp and electricity usage
        """

        if self.capacity == 0:
            return HpDemand(0.0, 0.0)

        # maximum thermal output given elec supply
        max_thermal_output = elec_supply * hp_performance.cop

        # demand met by hp is min of three arguments
        hp_demand = min(max_thermal_output, heat_demand, hp_performance.duty)
        hp_elec = hp_demand / hp_performance.cop

        return HpDemand(hp_demand, hp_elec)
