"""Uses generic regression analysis to predict performance.

See Staffel paper on review of domestic heat pumps for coefficients.
"""

import logging
import numpy as np

from .performance import PerformanceModel
from ..enums import HP

LOG = logging.getLogger(__name__)


class GenericRegression(PerformanceModel):
    def __init__(self, pump: HP):
        self.pump = pump

    @property
    def pump(self) -> HP:
        return self._pump

    @pump.setter
    def pump(self, pump: HP):
        if not isinstance(pump, HP):
            msg = f"{pump} is not a valid heat pump option, must be one of {[_.value for _ in HP]}"
            LOG.error(msg)
            raise KeyError(msg)
        self._pump = pump

    def cop(
        self, flow_temp: np.ndarray[float], ambient_temp: np.ndarray[float]
    ) -> np.ndarray[float]:
        """Array based COP calculation

        Args:
            flow_temp, array of flow temperatures in degrees C
            ambient_temp, array of ambient temperatures in degrees C

        Returns:
            array of COP values
        """
        # account for defrosting below 5 drg
        factor = np.ones(flow_temp.shape)
        sub_5 = ambient_temp <= 5.0
        factor[sub_5] = 0.9

        # Note that self.pump has already been validated
        if self.pump is HP.ASHP:
            return (
                6.81
                - 0.121 * (flow_temp - ambient_temp)
                + 0.00063 * (flow_temp - ambient_temp) ** 2
            ) * factor
        else:
            return (
                8.77
                - 0.15 * (flow_temp - ambient_temp)
                + 0.000734 * (flow_temp - ambient_temp) ** 2
            ) * factor

    def duty(self, ambient_temp: np.ndarray[float]) -> np.ndarray[float]:
        """Array based duty calculation

        Args:
            ambient_temp, array of ambient temperatures in degrees C

        Returns:
            array of duty values
        """
        # Note that self.pump has already been validated
        if self.pump is HP.ASHP:
            return 5.80 + 0.21 * (ambient_temp)
        else:
            return 9.37 + 0.30 * ambient_temp
