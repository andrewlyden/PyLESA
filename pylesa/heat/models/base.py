from abc import ABC, abstractmethod

class Base(ABC):
    """Base heat pump performance model"""
    @abstractmethod
    def cop(self):
        pass

    @abstractmethod
    def duty(self):
        pass