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
        self._cop_spec = cop_spec
        self._elec_capacity = elec_capacity
        self._efficiency = None
        self._set_efficiency(cop_spec, flow_temp_spec, return_temp_spec, ambient_temp_in_spec, ambient_temp_out_spec)

    @property
    def efficiency(self) -> float:
        """Heat pump efficiency which is static"""
        return self._efficiency

    def _cop_lorentz(self, flow_temp: float | np.ndarray[float], return_temp: float | np.ndarray[float],
                 ambient_temp_in: float | np.ndarray[float], ambient_temp_out: float | np.ndarray[float]) -> float | np.ndarray[float]:
        """Lorentz COP calculation based on EnergyPRO method"""
        t_high_mean = ((flow_temp - return_temp) /
                       (np.log((flow_temp + ABS_ZERO) /
                                 (return_temp + ABS_ZERO))))

        t_low_mean = ((ambient_temp_in - ambient_temp_out) /
                      (np.log((ambient_temp_in + ABS_ZERO) /
                                (ambient_temp_out + ABS_ZERO))))

        # lorentz cop is the highest theoretical cop
        return t_high_mean / (t_high_mean - t_low_mean)

    def _set_efficiency(self, cop_spec: float, flow_temp_spec: float, return_temp_spec: float,
                 ambient_temp_in_spec: float, ambient_temp_out_spec: float):
        """Set static heat pump efficiency

        Calculations of the lorentz model. starting with the mean temps fo
        for the temp flow and return of heat pump, t high mean
        and the ambient in and out temps, t low mean
        """
        # this gives the heat pump efficiency using the stated cop
        # the lorentz cop is calcualted for each timestep
        # then this is multiplied by the heat pump
        # efficiency to give actual cop
        self._efficiency = cop_spec / self._cop_lorentz(flow_temp_spec, return_temp_spec, ambient_temp_in_spec, ambient_temp_out_spec)

    def cop(self, flow_temp: np.ndarray[float], return_temp: np.ndarray[float],
                 ambient_temp_in: np.ndarray[float], ambient_temp_out: np.ndarray[float]) -> np.ndarray[float]:
        """Array COP calculation

        Calculates the cop based upon actual flow/return and ambient
        using heat pump efficiency

        Args:
            flow_temp, flow temperatures from heat pump
            return_temp, temperatures returning to heat pump
            ambient_temp_in, real-time
            ambient_temp_out , real-time

        Returns:
            Cop for timestep
        """
        return self.efficiency * self._cop_lorentz(flow_temp, return_temp, ambient_temp_in, ambient_temp_out)

    def duty(self, capacity: float) -> float:
        """Duty calculation

        Ensures capacity is not exceeded.

        Arguments:
            capacity,  electrical capacity of heat pump

        Returns:
            duty, which is the thermal output of the heat pump
        """
        return min(self._cop_spec * self._elec_capacity, capacity)