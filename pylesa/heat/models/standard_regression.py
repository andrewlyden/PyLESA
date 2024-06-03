import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

from .performance import PerformanceModel

LOG = logging.getLogger(__name__)


class StandardTestRegression(PerformanceModel):
    def __init__(
        self,
        xarr: np.ndarray,
        cosparr: np.ndarray,
        dutyarr: np.ndarray,
        degree: int = 2,
    ):
        """Regression analysis based on standard test condition data

        Trains a model on initialisation and predicts cop and duty

        Args:
            xarr: 2D array of flow and ambient temperatures
            cosparr: 2D array of COSP data of shape (N, 1)
            dutyarr: 2D array of duty data of shape (N, 1)
            degree: sklearn.preprocessing.PolynomialFeatures polynomial number (default=2)
        """
        self._degree = degree
        self._copmodel = None
        self._dutymodel = None
        self._train(xarr, cosparr, dutyarr)

    @property
    def copmodel(self) -> LinearRegression:
        return self._copmodel

    @property
    def dutymodel(self) -> LinearRegression:
        return self._dutymodel

    def _train(
        self, xarr: np.ndarray, cosparr: np.ndarray, dutyarr: np.ndarray
    ) -> None:
        """Trains the model

        Args:
            xarr: 2D array of flow and ambient temperatures
            cosparr: 2D array of COSP data of shape (N, 1)
            dutyarr: 2D array of duty data of shape (N, 1)

        Returns:
            None

        Raises:
            IndexError if input data shapes are incorrect
        """
        poly = PolynomialFeatures(degree=self._degree, include_bias=False)

        if len(xarr.shape) != 2:
            msg = f"Model training temperature data must have flow and ambient columns, data has {len(xarr.shape)} dimensions"
            LOG.error(msg)
            raise IndexError(msg)
        if xarr.shape[1] != 2:
            msg = f"Model training temperature data must have flow and ambient columns, data has {xarr.shape[1]} columns"
            LOG.error(msg)
            raise IndexError(msg)

        if isinstance(cosparr, pd.DataFrame) or isinstance(cosparr, pd.Series):
            cosparr = cosparr.values
        if len(cosparr.shape) == 1:
            cosparr = cosparr.reshape(-1, 1)

        if isinstance(dutyarr, pd.DataFrame) or isinstance(dutyarr, pd.Series):
            dutyarr = dutyarr.values
        if len(dutyarr.shape) == 1:
            dutyarr = dutyarr.reshape(-1, 1)

        if xarr.shape[0] != cosparr.shape[0] or xarr.shape[0] != dutyarr.shape[0]:
            msg = f"Temperature, cop and duty arrays must have same first dimension ({xarr.shape[0]})"
            LOG.error(msg)
            raise IndexError(msg)

        X_new = poly.fit_transform(xarr)
        Y_COSP_new = poly.fit_transform(cosparr)
        Y_duty_new = poly.fit_transform(dutyarr)

        model_cop = LinearRegression()
        model_cop.fit(X_new, Y_COSP_new)

        model_duty = LinearRegression()
        model_duty.fit(X_new, Y_duty_new)

        self._copmodel = model_cop
        self._dutymodel = model_duty

    def _fit(self, x: np.ndarray[float], x1: np.ndarray[float]) -> np.ndarray[float]:
        poly = PolynomialFeatures(degree=self._degree, include_bias=False)
        return poly.fit_transform(np.array([x, x1]).T)

    def cop(
        self, ambient: np.ndarray[float], flow: np.ndarray[float]
    ) -> np.ndarray[float]:
        """Predicts COP from regression model

        Args:
            ambient: ambient temperatures to predict COP
            flow: flow temperatures to predict COP

        Returns:
            Predicted COP value
        """
        pred_cop = self.copmodel.predict(self._fit(ambient, flow))
        return pred_cop[:, 0]

    def duty(
        self, ambient: np.ndarray[float], flow: np.ndarray[float]
    ) -> np.ndarray[float]:
        """Predicts duty from regression model

        Args:
            ambient: ambient temperatures to predict COP
            flow: flow temperatures to predict COP

        Returns:
            Predicted duty value
        """
        pred_duty = self.dutymodel.predict(self._fit(ambient, flow))
        return pred_duty[:, 0]
