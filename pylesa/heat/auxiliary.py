"""auxiliary modules

contains class for auxiliaries which covers
back up heaters
"""

from typing import Any, Dict


class Aux(object):

    def __init__(
        self, fuel: str, efficiency: float, fuel_info: Dict[str, Dict[str, Any]]
    ):
        """Back-up heater

        Args:
            fuel, name of fuel used
            efficiency, efficiency of fuel transform
            fuel_info, nested dictionary defining fuel cost and energy density
        """
        self.fuel = fuel
        self.efficiency = efficiency
        if fuel.lower() != "electric":
            self.cost = fuel_info[fuel]["cost"]
            self.energy_density = fuel_info[fuel]["energy_density"]

    def fuel_usage(self, demand: float) -> float:
        """Fuel used (units consistent with demand)

        Args:
            demand, unmet demand

        Returns:
            float, fuel used
        """
        return demand / self.efficiency
