import logging

from .performance import PerformanceModel

LOG = logging.getLogger(__name__)


class Simple(PerformanceModel):
    def __init__(self, cop: float, duty: float):
        self._cop = cop
        self._duty = duty

    def cop(self):
        return self._cop

    def duty(self):
        return self._duty
