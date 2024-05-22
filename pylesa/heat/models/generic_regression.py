"""Uses generic regression analysis to predict performance.

See Staffel paper on review of domestic heat pumps for coefficients.
"""
import logging

from .base import Base
from .constants import HP

LOG = logging.getLogger(__name__)

class GenericRegression(Base):
    def __init__(self, pump: HP):
        self.pump = pump

    def cop(self, flow_temp: float, ambient_temp: float) -> float:
        match self.pump:
            case HP.ASHP:
                return (6.81 -
                    0.121 * (flow_temp - ambient_temp) +
                    0.00063 * (flow_temp - ambient_temp) ** 2
                )
            case HP.GSHP | HP.WSHP:
                return (8.77 -
                    0.15 * (flow_temp - ambient_temp) +
                    0.000734 * (flow_temp - ambient_temp) ** 2
                )
            case _:
                msg = f"Cannot calculate cop for heatpump {self.pump}, must be one of {[HP.ASHP, HP.GSHP, HP.WSHP]}"
                LOG.error(msg)
                raise KeyError(msg)

    def duty(self, ambient_temp: float) -> float:
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