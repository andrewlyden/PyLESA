import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

from .performance import PerformanceModel

LOG = logging.getLogger(__name__)


class StandardTestRegression(PerformanceModel):
    def __init__(self, xarr: pd.Series | np.ndarray, cosparr: pd.Series | np.ndarray,
                 dutyarr: pd.Series | np.ndarray, degree: int = 2):
        """Regression analysis based on standard test condition data

        Trains a model on initialisation and predicts cop and duty

        Args:
            xarr: Array of flow / ambient temperatures
            cosparr: Array of COSP data
            dutyarr: Array of duty data
            degree: sklearn.preprocessing.PolynomialFeatures polynomial number (default=2)
        """
        self._xarr = xarr
        self._cosparr = cosparr
        self._dutyarr = dutyarr
        self._degree = degree
        self._copmodel = None
        self._dutymodel = None
        self.train()

    @property
    def copmodel(self) -> LinearRegression:
        return self._copmodel
    
    @property
    def dutymodel(self) -> LinearRegression:
        return self._dutymodel

    def train(self) -> None:
        """training model
        """
        poly = PolynomialFeatures(degree=self._degree, include_bias=False)

        X_new = poly.fit_transform(self._xarr)
        Y_COSP_new = poly.fit_transform(self._cosparr)
        Y_duty_new = poly.fit_transform(self._dutyarr)

        model_cop = LinearRegression()
        model_cop.fit(X_new, Y_COSP_new)

        model_duty = LinearRegression()
        model_duty.fit(X_new, Y_duty_new)

        self._copmodel = model_cop
        self._dutymodel = model_duty

    def cop(self, ambient: np.ndarray[float], flow: np.ndarray[float]) -> np.ndarray[float]:
        """Predicts COP from regression model
        
        Args:
            ambient: ambient temperature to predict COP
            flow: flow temperature to predict COP

        Returns:
            Predicted COP value
        """
        x_pred = np.array([ambient, flow]).swapaxes(0, 1)
        poly = PolynomialFeatures(degree=self._degree, include_bias=False)
        x_pred_new = poly.fit_transform(x_pred)
        pred_cop = self.copmodel.predict(x_pred_new)
        return pred_cop[:, 0]

    def duty(self, ambient: np.ndarray[float], flow: np.ndarray[float]) -> np.ndarray[float]:
        """Predicts duty from regression model

        Args:
            ambient: ambient temperature to predict COP
            flow: flow temperature to predict COP

        Returns:
            Predicted duty value
        """
        x_pred = np.array([ambient, flow]).swapaxes(0, 1)
        poly = PolynomialFeatures(degree=2, include_bias=False)
        x_pred_new = poly.fit_transform(x_pred)
        pred_duty = self.dutymodel.predict(x_pred_new)
        return pred_duty[:, 0]