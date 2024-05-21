import logging
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

LOG = logging.getLogger(__name__)

class StandardTestRegression(object):

    def __init__(self, data_x, data_COSP,
                 data_duty, degree=2):
        """regression analysis based on standard test condition data

        trains a model
        predicts cop and duty

        Arguments:
            data_x {dataframe} -- with flow temps and ambient temps
            data_COSP {dataframe} -- with cosp data for different data_X
            data_duty {dataframe} -- with duty data for different data_X

        Keyword Arguments:
            degree {number} -- polynomial number (default: {2})
        """
        self.data_x = data_x
        self.data_COSP = data_COSP
        self.data_duty = data_duty
        self.degree = degree

    def train(self):
        """training model
        """
        poly = PolynomialFeatures(degree=self.degree, include_bias=False)

        X_new = poly.fit_transform(self.data_x)
        Y_COSP_new = poly.fit_transform(self.data_COSP)
        Y_duty_new = poly.fit_transform(self.data_duty)

        model_cop = LinearRegression()
        model_cop.fit(X_new, Y_COSP_new)

        model_duty = LinearRegression()
        model_duty.fit(X_new, Y_duty_new)

        return {'COP_model': model_cop, 'duty_model': model_duty}

    def predict_COP(self, model, ambient_temp, flow_temp):
        """predicts COP from model

        Arguments:
            model {dic} -- cop and duty models in dic
            ambient_temp {float} --
            flow_temp {float} --

        Returns:
            float -- predicted COP
        """

        x_pred = np.array([ambient_temp, flow_temp]).reshape(1, -1)
        poly = PolynomialFeatures(degree=2, include_bias=False)
        x_pred_new = poly.fit_transform(x_pred)
        pred_cop = model.predict(x_pred_new)

        return float(pred_cop[:, 0])

    def predict_duty(self, model, ambient_temp, flow_temp):
        """predicts duty from regression model

        Arguments:
            model {dic} -- cop and duty models in dic
            ambient_temp {float} --
            flow_temp {float} --

        Returns:
            float -- predicted COP
        """

        x_pred = np.array([ambient_temp, flow_temp]).reshape(1, -1)
        poly = PolynomialFeatures(degree=2, include_bias=False)
        x_pred_new = poly.fit_transform(x_pred)
        pred_duty = model.predict(x_pred_new)

        return float(pred_duty[:, 0])