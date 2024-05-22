import logging

from .models import HP
from ..environment import weather

from .models.lorentz import Lorentz
from . import generic_regression
from .models.standard_regression import StandardTestRegression

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

        self.hp_type = HP[hp_type]
        self.modelling_approach = modelling_approach
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

    def performance(self):
        """performance over year of heat pump

        input a timestep from which gathers inputs
        a method for calculating the heat pump performance (cop and duty)
        for a timetsp
        outputs are dict containing

        Returns:
            dic -- cop and duty for each hour timestep in year
        """
        if self.capacity == 0:
            performance = []
            for timesteps in range(8760):
                # cop needs to be low to not break the mpc solver
                # duty being zero means it won't choose it anyway
                p = {'cop': 0.5, 'duty': 0}
                performance.append(p)
            return performance

        ambient_temp = self.heat_resource()['ambient_temp']

        if self.modelling_approach == 'Simple':
            cop_x = self.simple_cop
            duty_x = self.capacity

        elif self.modelling_approach == 'Lorentz':
            myLorentz = Lorentz(self.lorentz_inputs['cop'],
                                self.lorentz_inputs['flow_temp_spec'],
                                self.lorentz_inputs['return_temp_spec'],
                                self.lorentz_inputs['temp_ambient_in_spec'],
                                self.lorentz_inputs['temp_ambient_out_spec'],
                                self.lorentz_inputs['elec_capacity'])
            hp_eff = myLorentz.hp_eff()

        elif self.modelling_approach == 'Generic regression':
            duty_x = self.capacity

        elif self.modelling_approach == 'Standard test regression':
            myStandardRegression = StandardTestRegression(
                self.standard_test_regression_inputs['data_x'],
                self.standard_test_regression_inputs['data_COSP'],
                self.standard_test_regression_inputs['data_duty'])

        performance = []
        for timestep in range(8760):

            if self.modelling_approach == 'Simple':
                cop = cop_x
                hp_duty = duty_x

            elif self.modelling_approach == 'Lorentz':
                ambient_return = ambient_temp.iloc[timestep] - self.ambient_delta_t
                cop = myLorentz.calc_cop(hp_eff,
                                         self.flow_temp_source.iloc[timestep],
                                         self.return_temp.iloc[timestep],
                                         ambient_temp.iloc[timestep],
                                         ambient_return)
                hp_duty = myLorentz.calc_duty(self.capacity)

            elif self.modelling_approach == 'Generic regression':
                cop = generic_regression.cop(
                        self.hp_type,
                        self.flow_temp_source.iloc[timestep],
                        ambient_temp.iloc[timestep]
                    )

                # account for defrosting below 5 drg
                if ambient_temp.iloc[timestep] <= 5:
                    cop = 0.9 * cop

                hp_duty = duty_x

            elif self.modelling_approach == 'Standard test regression':
                hp_duty = myStandardRegression.duty(
                    ambient_temp.iloc[timestep],
                    self.flow_temp_source.iloc[timestep])

                # 15% reduction in performance if
                # data not done to standards
                if self.data_input == 'Integrated performance' or ambient_temp.iloc[timestep] > 5:
                    cop = myStandardRegression.cop(
                        ambient_temp.iloc[timestep],
                        self.flow_temp_source.iloc[timestep])

                elif self.data_input == 'Peak performance':
                    if self.hp_type == HP.ASHP:

                        if ambient_temp.iloc[timestep] <= 5:
                            cop = 0.9 * myStandardRegression.cop(
                                ambient_temp.iloc[timestep],
                                self.flow_temp_source.iloc[timestep])

            d = {'cop': cop, 'duty': hp_duty}
            performance.append(d)

        return performance

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