from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

import numpy as np

LOG = logging.getLogger(__name__)


@dataclass
class PerformanceValue:
    cop: float
    duty: float


@dataclass
class PerformanceArray:
    cop: np.ndarray[float]
    duty: np.ndarray[float]

    def __post_init__(self):
        if self.cop.shape != self.duty.shape:
            msg = f"cop (shape={self.cop.shape}) and duty (shape={self.duty.shape}) must be of same dimensions"
            LOG.error(msg)
            raise IndexError(msg)
        if len(self.cop.shape) > 1:
            msg = f"cop and duty arrays must be 1 dimensional"
            LOG.error(msg)
            raise IndexError(msg)

    def __iter__(self):
        for idx in range(self.cop.shape[0]):
            yield PerformanceValue(self.cop[idx], self.duty[idx])

    def __getitem__(self, index):
        return PerformanceValue(self.cop[index], self.duty[index])


class PerformanceModel(ABC):
    """Base heat pump performance model"""

    @abstractmethod
    def cop(self):
        pass

    @abstractmethod
    def duty(self):
        pass
