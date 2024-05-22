import math
import logging

LOG = logging.getLogger(__name__)

class Lorentz(object):

    def __init__(self, cop, flow_temp_spec, return_temp_spec,
                 ambient_temp_in_spec, ambient_temp_out_spec,
                 elec_capacity):
        """lorentz calculations and attributes

        based on EnergyPRO method

        Arguments:
            cop {float} -- cop at specified conditions
            flow_temp_spec {float} -- temperature from HP spec
            return_temp_spec {float} -- tempature to HP spec
            ambient_temp_in_spec {float} -- specificed
            ambient_temp_out_spec {float} -- spec
            elec_capacity {float} -- absolute
        """

        self.cop = cop
        self.flow_temp_spec = flow_temp_spec
        self.return_temp_spec = return_temp_spec
        self.ambient_temp_in_spec = ambient_temp_in_spec
        self.ambient_temp_out_spec = ambient_temp_out_spec
        self.elec_capacity = elec_capacity

    def hp_eff(self):
        """heat pump efficiency which is static

        # calcultaions of the lorentz model. starting with the mean temps fo
        # for the temp flow and return of heat pump, t high mean
        # and the ambient in and out temps, t low mean

        Returns:
            float -- efficiency of the heat pump
        """
        t_high_mean = ((self.flow_temp_spec - self.return_temp_spec) /
                       (math.log((self.flow_temp_spec + 273.15) /
                                 (self.return_temp_spec + 273.15))))

        t_low_mean = (
            (self.ambient_temp_in_spec - self.ambient_temp_out_spec) /
            (math.log((self.ambient_temp_in_spec + 273.15) /
                      (self.ambient_temp_out_spec + 273.15))))

        # lorentz cop is the highest theoretical cop
        cop_lorentz = t_high_mean / (t_high_mean - t_low_mean)

        # this gives the heat pump efficiency using the stated cop
        # the lorentz cop is calcualted for each timestep
        # then this is multiplied by the heat pump
        # efficiency to give actual cop
        hp_eff = self.cop / cop_lorentz

        return hp_eff

    def calc_cop(self, hp_eff, flow_temp, return_temp,
                 ambient_temp_in, ambient_temp_out):
        """cop for timestep

        calculates the cop based upon actual flow/retur and ambient
        uses heat pump efficiency from before

        Arguments:
            hp_eff {float} -- heat pump efficiency
            flow_temp {float} -- flow temperature from heat pump
            return_temp {float} -- temperature returning to heat pump
            ambient_temp_in {float} -- real-time
            ambient_temp_out {float} -- real-time

        Returns:
            float -- cop for timestep
        """

        t_high_mean = ((flow_temp - return_temp) /
                       (math.log((flow_temp + 273.15) /
                                 (return_temp + 273.15))))

        t_low_mean = ((ambient_temp_in - ambient_temp_out) /
                      (math.log((ambient_temp_in + 273.15) /
                                (ambient_temp_out + 273.15))))

        cop_lorentz = t_high_mean / (t_high_mean - t_low_mean)

        cop = hp_eff * cop_lorentz

        return cop

    def calc_duty(self, capacity):
        """duty for timestep

        calculates duty for timestep, ensures this is not exceeded

        Arguments:
            capacity {float} -- electrical capacity of heat pump

        Returns:
            float -- duty is the thermal output of the heat pump
        """

        duty_max = self.cop * self.elec_capacity
        if duty_max >= capacity:
            duty = capacity
        elif duty_max < capacity:
            duty = duty_max

        return duty