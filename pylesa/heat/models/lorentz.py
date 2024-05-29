import math
import numpy as np
import logging

from .constants import ABS_ZERO
from .performance import PerformanceModel

LOG = logging.getLogger(__name__)

class Lorentz(PerformanceModel):

    def __init__(self, cop_spec: float, flow_temp_spec: float, return_temp_spec: float,
                 ambient_temp_in_spec: float, ambient_temp_out_spec: float,
                 elec_capacity: float):
        """Lorentz calculations and attributes

        Based on EnergyPRO method.

        Arguments:
            cop_spec, cop at specified conditions
            flow_temp_spec, temperature from HP spec
            return_temp_spec, tempature to HP spec
            ambient_temp_in_spec, specificed
            ambient_temp_out_spec, spec
            elec_capacity, absolute
        """

        self.cop_spec = cop_spec
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
                       (math.log((self.flow_temp_spec + ABS_ZERO) /
                                 (self.return_temp_spec + ABS_ZERO))))

        t_low_mean = (
            (self.ambient_temp_in_spec - self.ambient_temp_out_spec) /
            (math.log((self.ambient_temp_in_spec + ABS_ZERO) /
                      (self.ambient_temp_out_spec + ABS_ZERO))))

        # lorentz cop is the highest theoretical cop
        cop_lorentz = t_high_mean / (t_high_mean - t_low_mean)

        # this gives the heat pump efficiency using the stated cop
        # the lorentz cop is calcualted for each timestep
        # then this is multiplied by the heat pump
        # efficiency to give actual cop
        hp_eff = self.cop_spec / cop_lorentz

        return hp_eff

    def cop(self, flow_temp: np.ndarray[float], return_temp: np.ndarray[float],
                 ambient_temp_in: np.ndarray[float], ambient_temp_out: np.ndarray[float]) -> np.ndarray[float]:
        """Array COP calculation

        Calculates the cop based upon actual flow/return and ambient
        uses heat pump efficiency from before

        Args:
            flow_temp, flow temperatures from heat pump
            return_temp, temperatures returning to heat pump
            ambient_temp_in, real-time
            ambient_temp_out , real-time

        Returns:
            Cop for timestep
        """
        t_high_mean = ((flow_temp - return_temp) /
                       (np.log((flow_temp + ABS_ZERO) /
                                 (return_temp + ABS_ZERO))))

        t_low_mean = ((ambient_temp_in - ambient_temp_out) /
                      (np.log((ambient_temp_in + ABS_ZERO) /
                                (ambient_temp_out + ABS_ZERO))))

        cop_lorentz = t_high_mean / (t_high_mean - t_low_mean)

        cop = self.hp_eff() * cop_lorentz

        return cop

    def duty(self, capacity: float) -> float:
        """Duty calculation

        Ensures capacity is not exceeded.

        TODO: consider numpy array implementation

        Arguments:
            capacity {float} -- electrical capacity of heat pump

        Returns:
            float -- duty is the thermal output of the heat pump
        """
        duty_max = self.cop_spec * self.elec_capacity
        if duty_max >= capacity:
            duty = capacity
        elif duty_max < capacity:
            duty = duty_max

        return duty