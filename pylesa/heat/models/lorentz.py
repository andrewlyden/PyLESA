import math
import logging

from .base import Base

LOG = logging.getLogger(__name__)

class Lorentz(Base):

    def __init__(self, cop: float, flow_temp_spec: float, return_temp_spec: float,
                 ambient_temp_in_spec: float, ambient_temp_out_spec: float,
                 elec_capacity: float):
        """Lorentz calculations and attributes

        Based on EnergyPRO method.

        Arguments:
            cop, cop at specified conditions
            flow_temp_spec, temperature from HP spec
            return_temp_spec, tempature to HP spec
            ambient_temp_in_spec, specificed
            ambient_temp_out_spec, spec
            elec_capacity, absolute
        """

        self.cop = cop
        self.flow_temp_spec = flow_temp_spec
        self.return_temp_spec = return_temp_spec
        self.ambient_temp_in_spec = ambient_temp_in_spec
        self.ambient_temp_out_spec = ambient_temp_out_spec
        self.elec_capacity = elec_capacity

    def hp_eff(self) -> float:
        """heat pump efficiency which is static

        Calculations of the lorentz model. starting with the mean temps fo
        for the temp flow and return of heat pump, t high mean
        and the ambient in and out temps, t low mean

        Returns:
            Efficiency of the heat pump
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

    def cop(self, hp_eff: float, flow_temp: float, return_temp: float,
                 ambient_temp_in: float, ambient_temp_out: float) -> float:
        """cop for timestep

        calculates the cop based upon actual flow/return and ambient
        uses heat pump efficiency from before

        Args:
            hp_eff, heat pump efficiency
            flow_temp, flow temperature from heat pump
            return_temp, temperature returning to heat pump
            ambient_temp_in, real-time
            ambient_temp_out , real-time

        Returns:
            Cop for timestep
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

    def duty(self, capacity):
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