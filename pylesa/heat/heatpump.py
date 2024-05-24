import logging
import numpy as np

from .models import HP, Lorentz, StandardTestRegression, GenericRegression, PerformanceData, PerformanceModel, Simple
from ..constants import ANNUAL_HOURS
from ..environment import weather

LOG = logging.getLogger(__name__)

class HeatPump(object):
    def __init__(self, hp_type, modelling_approach,
                 capacity, ambient_delta_t,
                 minimum_runtime, minimum_output, data_input,
                 flow_temp_source, return_temp,
                 hp_ambient_temp,
                 simple_cop=None,
                 lorentz_inputs=None,
                 generic_regression_inputs=None,
                 standard_test_regression_inputs=None
                 ):
        """heat pump class object

        Arguments:
            hp_type {string} -- type of heatpump, ASHP, WSHP, GSHP
            modelling_approach {str} -- simple, lorentz,
                                        generic, standard regression
            capacity {float} -- thermal capacity of heat pump
            ambient_delta_t {int} -- drop in ambient source temperature
                                     from inlet to outlet
            minimum_runtime {string} -- fixed or variable speed compressor
            data_input {str} -- type of data input, peak or integrated
            flow_temp {dataframe} -- required temperatures out of HP
            return_temp {dataframe} -- inlet temp to HP
            weather {dic} -- ambient conditions of heat source

        Keyword Arguments: all these are for inputs, bar simple,
                           for different modelling approaches
            simple_cop {float} -- only COP for simple (default: {None})
            lorentz_inputs {dic} -- (default: {None})
            generic_regression_inputs {dic} -- (default: {None})
            standard_test_regression_inputs {dic} -- (default: {None})
        """
        self._model = None
        self.model = modelling_approach

        self.hp_type = HP[hp_type]
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
        self.generic_regression_inputs = generic_regression_inputs
        self.standard_test_regression_inputs = standard_test_regression_inputs

    @property
    def model(self) -> PerformanceModel:
        return self._model
    
    @model.setter
    def model(self, approach):
        match approach:
            case "Simple":
                if self.simple_cop is None:
                    msg = f"Heat pump performance model ({Simple}) cannot be initiated with simple_cop=None"
                    LOG.error(msg)
                    raise ValueError(msg)
                self._model = Simple(self.simple_cop, self.capacity)

            case "Lorentz":
                if self.lorentz_inputs is None:
                    msg = f"Heat pump performance model ({Lorentz}) cannot be initiated with lorentz_inputs=None"
                    LOG.error(msg)
                    raise ValueError(msg)
                self._model = Lorentz(self.lorentz_inputs['cop'],
                    self.lorentz_inputs['flow_temp_spec'],
                    self.lorentz_inputs['return_temp_spec'],
                    self.lorentz_inputs['temp_ambient_in_spec'],
                    self.lorentz_inputs['temp_ambient_out_spec'],
                    self.lorentz_inputs['elec_capacity']
                )

            case "Generic regression":
                # Raises error if hp_type is invalid
                self._model = GenericRegression(self.hp_type)

            case "Standard test regression":
                if self.standard_test_regression_inputs is None:
                    msg = f"Heat pump performance model ({StandardTestRegression}) cannot be initiated with standard_test_regression_inputs=None"
                    LOG.error(msg)
                    raise ValueError(msg)
                self._model = StandardTestRegression(
                    self.standard_test_regression_inputs['data_x'],
                    self.standard_test_regression_inputs['data_COSP'],
                    self.standard_test_regression_inputs['data_duty']
                )
            
            case _:
                msg = f"Performance model {approach} is not valid"
                LOG.error(msg)
                raise KeyError(msg)

    def heat_resource(self):
        """accessing the heat resource

        takes the hp resource from the weather class

        Returns:
            dataframe -- ambient temperature for heat source of heat pump
        """

        HP_resource = weather.Weather(
            air_temperature=self.hp_ambient_temp['air_temperature'],
            water_temperature=self.hp_ambient_temp['water_temperature']).heatpump()

        if self.hp_type == HP.ASHP:

            HP_resource = HP_resource.rename(
                columns={'air_temperature': 'ambient_temp'})
            return HP_resource[['ambient_temp']]

        elif self.hp_type == HP.WSHP:

            HP_resource = HP_resource.rename(
                columns={'water_temperature': 'ambient_temp'})
            return HP_resource[['ambient_temp']]

        else:
            msg = f"Invalid heat pump type: {self.hp_type}, must be {HP.ASHP} or {HP.WSHP}"
            LOG.error(msg)
            raise ValueError(msg)
    
    def performance(self) -> PerformanceData:
        """performance over year of heat pump

        input a timestep from which gathers inputs
        a method for calculating the heat pump performance (cop and duty)
        for a timetsp
        outputs are dict containing

        Returns:
            Performance object defining cop and duty for each hour timestep in year
        """
        if self.capacity == 0:
            # TODO: change mpc to be clearer about how it uses cop and duty
            # cop needs to be low to not break the mpc solver
            # duty being zero means it won't choose it anyway
            cop = np.empty((ANNUAL_HOURS,)).fill(0.5)
            duty = np.zeros((ANNUAL_HOURS,))
            return PerformanceData(cop, duty)

        ambient_temp = self.heat_resource()['ambient_temp']

        duty_x = self.capacity

        match self.model.__class__:
            case Simple.__class__:
                return PerformanceData(
                    self.model.cop,
                    self.model.duty
                )

            case Lorentz.__class__:
                return PerformanceData(
                    self.model.cop(
                        self.flow_temp_source.iloc[timestep],
                        self.return_temp.iloc[timestep],
                        ambient_temp.iloc[timestep],
                        ambient_return
                    ),
                    self.model.duty(self.capacity)
                )

            case GenericRegression.__class__:
                return PerformanceData(
                    self.model.cop(
                        self.flow_temp_source.iloc[timestep],
                        ambient_temp.iloc[timestep]
                    ),
                    duty_x
                )

            case StandardTestRegression.__class__:
                # 15% reduction in performance if
                # data not done to standards
                if self.data_input == 'Integrated performance' or ambient_temp.iloc[timestep] > 5:
                    cop = self.model.cop(
                        ambient_temp.iloc[timestep],
                        self.flow_temp_source.iloc[timestep])

                elif self.data_input == 'Peak performance':
                    if self.hp_type == HP.ASHP:

                        if ambient_temp.iloc[timestep] <= 5:
                            cop = 0.9 * self.model.cop(
                                ambient_temp.iloc[timestep],
                                self.flow_temp_source.iloc[timestep])
                    else:
                        msg = f"Peak performance option not available for {self.hp_type}"
                        LOG.error(msg)
                        raise ValueError(msg)
                else:
                    msg = f"{self.data_input} is not valid for {self.model.__class__}"
                    LOG.error(msg)
                    raise ValueError(msg)
                    
                return PerformanceData(
                    cop,
                    self.model.duty(
                        ambient_temp.iloc[timestep],
                        self.flow_temp_source.iloc[timestep]
                    )
                )
            

    def elec_usage(self, demand, hp_performance):
        """electricity usage of hp for timestep given a thermal demand

        calculates the electrical usage of the heat pump given a heat demand
        outputs a dataframe of heat demand, heat pump heat demand,
        heat pump elec demand, cop, duty, and leftover
        (only non-zero for fixed speed HP)

        Arguments:
            timestep {int} -- timestep to be calculated
            demand {float} -- thermal demand to be met by heat pump
            hp_performance {dic} -- dic containing the cop and duty
                                    for timesteps over year

        Returns:
            dic -- heat demand to be met, cop, duty,
                   heat demand met by hp, electricity usage of heat pump
        """

        if self.capacity == 0:
            return {'hp_demand': 0.0, 'hp_elec': 0.0}

        cop = hp_performance['cop']
        duty = hp_performance['duty']

        max_elec_usage = demand / cop
        max_elec_cap = duty / cop
        hp_elec = min(max_elec_usage, max_elec_cap)
        hp_demand = hp_elec * cop

        d = {'hp_demand': hp_demand,
             'hp_elec': hp_elec}

        return d

    def thermal_output(self, elec_supply,
                       hp_performance, heat_demand):
        """thermal output from a given electricity supply

        Arguments:
            timestep {int} -- timestep to be modelled
            elec_supply {float} -- electricity supply used by heat pump
            hp_performance {dic} -- dic containing the cop and duty
                                    for timesteps over year
            heat_demand {float} -- heat demand to be met of timestep

        Returns:
            dic -- max_thermal_output, heat demand met by hp,
                   electricity usage of heat pump
        """

        if self.capacity == 0:
            return {'hp_demand': 0.0, 'hp_elec': 0.0}

        cop = hp_performance['cop']
        duty = hp_performance['duty']

        # maximum thermal output given elec supply
        max_thermal_output = elec_supply * cop

        # demand met by hp is min of three arguments
        hp_demand = min(max_thermal_output, heat_demand, duty)
        hp_elec = hp_demand / cop

        d = {'hp_demand': hp_demand,
             'hp_elec': hp_elec}

        return d