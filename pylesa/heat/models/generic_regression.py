"""Uses generic regression analysis to predict performance.

See Staffel paper on review of domestic heat pumps for coefficients.
"""
import logging
import numpy as np

from .performance import PerformanceModel
from .constants import HP

LOG = logging.getLogger(__name__)

class GenericRegression(PerformanceModel):
    def __init__(self, pump: HP):
        self.pump = pump

    @property
    def pump(self):
        return self._pump
    
    @pump.setter
    def pump(self, pump):
        if pump not in HP:
            msg = f"{pump} is not a valid heat pump option, must be one of {[HP.ASHP, HP.GSHP, HP.WSHP]}"
            LOG.error(msg)
            raise KeyError(msg)
        self._pump = pump

    def cop(self, flow_temp: np.ndarray[float], ambient_temp: np.ndarray[float]) -> np.ndarray[float]:
        # account for defrosting below 5 drg
        factor = np.ones(flow_temp.shape)
        sub_5 = ambient_temp <= 5.
        factor[sub_5] = 0.9

        match self.pump:

            case HP.ASHP:
                return (6.81 -
                    0.121 * (flow_temp - ambient_temp) +
                    0.00063 * (flow_temp - ambient_temp) ** 2
                ) * factor
            
            case HP.GSHP | HP.WSHP:
                return (8.77 -
                    0.15 * (flow_temp - ambient_temp) +
                    0.000734 * (flow_temp - ambient_temp) ** 2
                ) * factor
            
            case _:
                msg = f"Cannot calculate cop for heatpump {self.pump}, must be one of {[HP.ASHP, HP.GSHP, HP.WSHP]}"
                LOG.error(msg)
                raise KeyError(msg)

    def duty(self, ambient_temp: np.ndarray[float]) -> np.ndarray[float]:
        match self.pump:

            case HP.ASHP:
                return (5.80 +
                    0.21 * (ambient_temp)
                )
            
            case HP.GSHP | HP.WSHP:
                return (9.37 +
                    0.30 * ambient_temp
                )
            
            case _:
                msg = f"Cannot calculate cop for heatpump {self.pump}, must be one of {[HP.ASHP, HP.GSHP, HP.WSHP]}"
                LOG.error(msg)
                raise KeyError(msg)