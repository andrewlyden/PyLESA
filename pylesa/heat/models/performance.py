from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

@dataclass
class PerformanceData:
    cop: np.ndarray
    duty: np.ndarray

class PerformanceModel(ABC):
    """Base heat pump performance model"""
    @abstractmethod
    def cop(self):
        pass

    @abstractmethod
    def duty(self):
        pass