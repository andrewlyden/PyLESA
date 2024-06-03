"""auxiliary modules

contains class for auxiliaries which covers
back up heaters
"""

import logging
from typing import Any, Dict

from .enums import Fuel

LOG = logging.getLogger(__name__)


class Aux(object):

    def __init__(
        self, fuel: Fuel, efficiency: float, fuel_info: Dict[Fuel, Dict[str, float]]
    ):
        """Back-up heater

        Args:
            fuel, name of fuel used
            efficiency, efficiency of fuel transform
            fuel_info, nested dictionary defining fuel cost and energy density
        """
        self._fuel_info = fuel_info
        self.fuel = fuel
        self.efficiency = efficiency

    @property
    def fuel(self) -> Fuel:
        return self._fuel

    @fuel.setter
    def fuel(self, fuel: Fuel):
        if fuel not in Fuel:
            msg = f"Invalid fuel type: {fuel}, must be one of {[_.value for _ in Fuel]}"
            LOG.error(msg)
            raise ValueError(msg)
        self._fuel = fuel

        if self.fuel is Fuel.ELECTRIC:
            self.cost = None
            self.energy_density = None
        else:
            if self.fuel not in self._fuel_info:
                msg = f"Fuel info is not available for fuel type: {self.fuel}, please specify one of {list(self._fuel_info.keys())}"
                LOG.error(msg)
                raise KeyError(msg)
            self.cost = self._fuel_info[self.fuel]["cost"]
            self.energy_density = self._fuel_info[fuel]["energy_density"]

    def fuel_usage(self, demand: float) -> float:
        """Fuel used (units consistent with demand)

        Args:
            demand, unmet demand

        Returns:
            float, fuel used
        """
        return demand / self.efficiency
