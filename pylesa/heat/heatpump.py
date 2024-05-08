"""Heat pump module

Modelling a heat pump with modelling approaches of
simple, lorentz, generic regression, and standard test regression

"""
import os
import math

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

from .. import tools as t
from ..io import inputs
from ..environment import weather

plt.style.use('ggplot')
plt.rcParams.update({'font.size': 22})


def perf(name, subname):

    myInputs = inputs.Inputs(name, subname)
    input_weather = myInputs.weather()
    inputs_basics = myInputs.heatpump_basics()
    modelling_approach = inputs_basics['modelling_approach']

    if modelling_approach == 'Simple':

        inputs_simple = myInputs.heatpump_simple()
        inputs_demands = myInputs.demands()

        myHeatPump = HeatPump(
            inputs_basics['heat_pump_type'],
            inputs_basics['modelling_approach'],
            inputs_basics['capacity'],
            inputs_basics['ambient_delta_t'],
            inputs_basics['minimum_runtime'],
            inputs_basics['minimum_output'],
            inputs_basics['data_input'],
            inputs_demands['source_temp'],
            inputs_demands['return_temp_DH'],
            input_weather,
            simple_cop=inputs_simple)

        return myHeatPump.performance()

    elif modelling_approach == 'Lorentz':

        inputs_lorentz = myInputs.heatpump_lorentz()
        inputs_demands = myInputs.demands()

        myHeatPump = HeatPump(
            inputs_basics['heat_pump_type'],
            inputs_basics['modelling_approach'],
            inputs_basics['capacity'],
            inputs_basics['ambient_delta_t'],
            inputs_basics['minimum_runtime'],
            inputs_basics['minimum_output'],
            inputs_basics['data_input'],
            inputs_demands['source_temp'],
            inputs_demands['return_temp_DH'],
            input_weather,
            lorentz_inputs=inputs_lorentz)

        return myHeatPump.performance()

    elif modelling_approach == 'Generic regression':

        inputs_demands = myInputs.demands()

        myHeatPump = HeatPump(
            inputs_basics['heat_pump_type'],
            inputs_basics['modelling_approach'],
            inputs_basics['capacity'],
            inputs_basics['ambient_delta_t'],
            inputs_basics['minimum_runtime'],
            inputs_basics['minimum_output'],
            inputs_basics['data_input'],
            inputs_demands['source_temp'],
            inputs_demands['return_temp_DH'],
            input_weather)

        return myHeatPump.performance()

    elif modelling_approach == 'Standard test regression':

        inputs_standard_regression = myInputs.heatpump_standard_regression()
        inputs_demands = myInputs.demands()

        myHeatPump = HeatPump(
            inputs_basics['heat_pump_type'],
            inputs_basics['modelling_approach'],
            inputs_basics['capacity'],
            inputs_basics['ambient_delta_t'],
            inputs_basics['minimum_runtime'],
            inputs_basics['minimum_output'],
            inputs_basics['data_input'],
            inputs_demands['source_temp'],
            inputs_demands['return_temp_DH'],
            input_weather,
            standard_test_regression_inputs=inputs_standard_regression)

        return myHeatPump.performance()


class HeatPump(object):

    def __init__(self, hp_type, modelling_approach,
                 capacity, ambient_delta_t,
                 minimum_runtime, minimum_output, data_input,
                 flow_temp_source, return_temp,
                 hp_ambient_temp,
                 simple_cop=None,
                 lorentz_inputs=None,
                 generic_regression_inputs=None,
                 standard_test_regression_inputs=None
                 ):
        """heat pump class object

        Arguments:
            hp_type {string} -- type of heatpump, ASHP, WSHP, GSHP
            modelling_approach {str} -- simple, lorentz,
                                        generic, standard regression
            capacity {float} -- thermal capacity of heat pump
            ambient_delta_t {int} -- drop in ambient source temperature
                                     from inlet to outlet
            minimum_runtime {string} -- fixed or variable speed compressor
            data_input {str} -- type of data input, peak or integrated
            flow_temp {dataframe} -- required temperatures out of HP
            return_temp {dataframe} -- inlet temp to HP
            weather {dic} -- ambient conditions of heat source

        Keyword Arguments: all these are for inputs, bar simple,
                           for different modelling approaches
            simple_cop {float} -- only COP for simple (default: {None})
            lorentz_inputs {dic} -- (default: {None})
            generic_regression_inputs {dic} -- (default: {None})
            standard_test_regression_inputs {dic} -- (default: {None})
        """

        self.hp_type = hp_type
        self.modelling_approach = modelling_approach
        self.capacity = capacity
        self.ambient_delta_t = ambient_delta_t
        self.minimum_runtime = minimum_runtime
        self.minimum_output = minimum_output
        self.data_input = data_input
        self.flow_temp_source = flow_temp_source
        self.return_temp = return_temp
        self.hp_ambient_temp = hp_ambient_temp

        self.simple_cop = simple_cop
        self.lorentz_inputs = lorentz_inputs
        self.generic_regression_inputs = generic_regression_inputs
        self.standard_test_regression_inputs = standard_test_regression_inputs

    def heat_resource(self):
        """accessing the heat resource

        takes the hp resource from the weather class

        Returns:
            dataframe -- ambient temperature for heat source of heat pump
        """

        HP_resource = weather.Weather(
            air_temperature=self.hp_ambient_temp['air_temperature'],
            water_temperature=self.hp_ambient_temp['water_temperature']).heatpump()

        if self.hp_type == 'ASHP':

            HP_resource = HP_resource.rename(
                columns={'air_temperature': 'ambient_temp'})
            return HP_resource[['ambient_temp']]

        elif self.hp_type == 'WSHP':

            HP_resource = HP_resource.rename(
                columns={'water_temperature': 'ambient_temp'})
            return HP_resource[['ambient_temp']]

        else:
            print('ERROR invalid heat pump type')

    def performance(self):
        """performance over year of heat pump

        input a timestep from which gathers inputs
        a method for calculating the heat pump performance (cop and duty)
        for a timetsp
        outputs are dict containing

        Returns:
            dic -- cop and duty for each hour timestep in year
        """
        if self.capacity == 0:
            performance = []
            for timesteps in range(8760):
                # cop needs to be low to not break the mpc solver
                # duty being zero means it won't choose it anyway
                p = {'cop': 0.5, 'duty': 0}
                performance.append(p)
            return performance

        ambient_temp = self.heat_resource()['ambient_temp']

        if self.modelling_approach == 'Simple':
            cop_x = self.simple_cop
            duty_x = self.capacity

        elif self.modelling_approach == 'Lorentz':
            myLorentz = Lorentz(self.lorentz_inputs['cop'],
                                self.lorentz_inputs['flow_temp_spec'],
                                self.lorentz_inputs['return_temp_spec'],
                                self.lorentz_inputs['temp_ambient_in_spec'],
                                self.lorentz_inputs['temp_ambient_out_spec'],
                                self.lorentz_inputs['elec_capacity'])
            hp_eff = myLorentz.hp_eff()

        elif self.modelling_approach == 'Generic regression':
            myGenericRegression = GenericRegression()
            duty_x = self.capacity

        elif self.modelling_approach == 'Standard test regression':
            myStandardRegression = StandardTestRegression(
                self.standard_test_regression_inputs['data_x'],
                self.standard_test_regression_inputs['data_COSP'],
                self.standard_test_regression_inputs['data_duty'])
            models = myStandardRegression.train()
            COP_model = models['COP_model']
            duty_model = models['duty_model']

        performance = []
        for timestep in range(8760):

            if self.modelling_approach == 'Simple':
                cop = cop_x
                hp_duty = duty_x

            elif self.modelling_approach == 'Lorentz':
                ambient_return = ambient_temp[timestep] - self.ambient_delta_t
                cop = myLorentz.calc_cop(hp_eff,
                                         self.flow_temp_source[timestep],
                                         self.return_temp[timestep],
                                         ambient_temp[timestep],
                                         ambient_return)
                hp_duty = myLorentz.calc_duty(self.capacity)

            elif self.modelling_approach == 'Generic regression':
                if self.hp_type == 'ASHP':
                    cop = myGenericRegression.ASHP_cop(
                        self.flow_temp_source[timestep],
                        ambient_temp[timestep])

                elif self.hp_type == 'GSHP' or self.hp_type == 'WSHP':
                    cop = myGenericRegression.GSHP_cop(
                        self.flow_temp_source[timestep],
                        ambient_temp[timestep])

                # account for defrosting below 5 drg
                if ambient_temp[timestep] <= 5:
                    cop = 0.9 * cop

                hp_duty = duty_x

            elif self.modelling_approach == 'Standard test regression':
                hp_duty = myStandardRegression.predict_duty(
                    duty_model,
                    ambient_temp[timestep],
                    self.flow_temp_source[timestep])

                # 15% reduction in performance if
                # data not done to standards
                if self.data_input == 'Integrated performance' or ambient_temp[timestep] > 5:
                    cop = myStandardRegression.predict_COP(
                        COP_model,
                        ambient_temp[timestep],
                        self.flow_temp_source[timestep])

                elif self.data_input == 'Peak performance':
                    if self.hp_type == 'ASHP':

                        if ambient_temp[timestep] <= 5:
                            cop = 0.9 * myStandardRegression.predict_COP(
                                COP_model,
                                ambient_temp[timestep],
                                self.flow_temp_source[timestep])

            d = {'cop': cop, 'duty': hp_duty}
            performance.append(d)

        return performance

    def elec_usage(self, demand, hp_performance):
        """electricity usage of hp for timestep given a thermal demand

        calculates the electrical usage of the heat pump given a heat demand
        outputs a dataframe of heat demand, heat pump heat demand,
        heat pump elec demand, cop, duty, and leftover
        (only non-zero for fixed speed HP)

        Arguments:
            timestep {int} -- timestep to be calculated
            demand {float} -- thermal demand to be met by heat pump
            hp_performance {dic} -- dic containing the cop and duty
                                    for timesteps over year

        Returns:
            dic -- heat demand to be met, cop, duty,
                   heat demand met by hp, electricity usage of heat pump
        """

        if self.capacity == 0:
            return {'hp_demand': 0.0, 'hp_elec': 0.0}

        cop = hp_performance['cop']
        duty = hp_performance['duty']

        max_elec_usage = demand / cop
        max_elec_cap = duty / cop
        hp_elec = min(max_elec_usage, max_elec_cap)
        hp_demand = hp_elec * cop

        d = {'hp_demand': hp_demand,
             'hp_elec': hp_elec}

        return d

    def thermal_output(self, elec_supply,
                       hp_performance, heat_demand):
        """thermal output from a given electricity supply

        Arguments:
            timestep {int} -- timestep to be modelled
            elec_supply {float} -- electricity supply used by heat pump
            hp_performance {dic} -- dic containing the cop and duty
                                    for timesteps over year
            heat_demand {float} -- heat demand to be met of timestep

        Returns:
            dic -- max_thermal_output, heat demand met by hp,
                   electricity usage of heat pump
        """

        if self.capacity == 0:
            return {'hp_demand': 0.0, 'hp_elec': 0.0}

        cop = hp_performance['cop']
        duty = hp_performance['duty']

        # maximum thermal output given elec supply
        max_thermal_output = elec_supply * cop

        # demand met by hp is min of three arguments
        hp_demand = min(max_thermal_output, heat_demand, duty)
        hp_elec = hp_demand / cop

        d = {'hp_demand': hp_demand,
             'hp_elec': hp_elec}

        return d


class Lorentz(object):

    def __init__(self, cop, flow_temp_spec, return_temp_spec,
                 ambient_temp_in_spec, ambient_temp_out_spec,
                 elec_capacity):
        """lorentz calculations and attributes

        based on EnergyPRO method

        Arguments:
            cop {float} -- cop at specified conditions
            flow_temp_spec {float} -- temperature from HP spec
            return_temp_spec {float} -- tempature to HP spec
            ambient_temp_in_spec {float} -- specificed
            ambient_temp_out_spec {float} -- spec
            elec_capacity {float} -- absolute
        """

        self.cop = cop
        self.flow_temp_spec = flow_temp_spec
        self.return_temp_spec = return_temp_spec
        self.ambient_temp_in_spec = ambient_temp_in_spec
        self.ambient_temp_out_spec = ambient_temp_out_spec
        self.elec_capacity = elec_capacity

    def hp_eff(self):
        """heat pump efficiency which is static

        # calcultaions of the lorentz model. starting with the mean temps fo
        # for the temp flow and return of heat pump, t high mean
        # and the ambient in and out temps, t low mean

        Returns:
            float -- efficiency of the heat pump
        """
        t_high_mean = ((self.flow_temp_spec - self.return_temp_spec) /
                       (math.log((self.flow_temp_spec + 273.15) /
                                 (self.return_temp_spec + 273.15))))

        t_low_mean = (
            (self.ambient_temp_in_spec - self.ambient_temp_out_spec) /
            (math.log((self.ambient_temp_in_spec + 273.15) /
                      (self.ambient_temp_out_spec + 273.15))))

        # lorentz cop is the highest theoretical cop
        cop_lorentz = t_high_mean / (t_high_mean - t_low_mean)

        # this gives the heat pump efficiency using the stated cop
        # the lorentz cop is calcualted for each timestep
        # then this is multiplied by the heat pump
        # efficiency to give actual cop
        hp_eff = self.cop / cop_lorentz

        return hp_eff

    def calc_cop(self, hp_eff, flow_temp, return_temp,
                 ambient_temp_in, ambient_temp_out):
        """cop for timestep

        calculates the cop based upon actual flow/retur and ambient
        uses heat pump efficiency from before

        Arguments:
            hp_eff {float} -- heat pump efficiency
            flow_temp {float} -- flow temperature from heat pump
            return_temp {float} -- temperature returning to heat pump
            ambient_temp_in {float} -- real-time
            ambient_temp_out {float} -- real-time

        Returns:
            float -- cop for timestep
        """

        t_high_mean = ((flow_temp - return_temp) /
                       (math.log((flow_temp + 273.15) /
                                 (return_temp + 273.15))))

        t_low_mean = ((ambient_temp_in - ambient_temp_out) /
                      (math.log((ambient_temp_in + 273.15) /
                                (ambient_temp_out + 273.15))))

        cop_lorentz = t_high_mean / (t_high_mean - t_low_mean)

        cop = hp_eff * cop_lorentz

        return cop

    def calc_duty(self, capacity):
        """duty for timestep

        calculates duty for timestep, ensures this is not exceeded

        Arguments:
            capacity {float} -- electrical capacity of heat pump

        Returns:
            float -- duty is the thermal output of the heat pump
        """

        duty_max = self.cop * self.elec_capacity
        if duty_max >= capacity:
            duty = capacity
        elif duty_max < capacity:
            duty = duty_max

        return duty


class GenericRegression(object):
    """uses generic regression analysis to predict performance

    see Staffel paper on review of domestic heat pumps for coefficients
    """

    def ASHP_cop(self, flow_temp, ambient_temp):

        cop = (6.81 -
               0.121 * (flow_temp - ambient_temp) +
               0.00063 * (flow_temp - ambient_temp) ** 2
               )
        return cop

    def ASHP_duty(self, flow_temp, ambient_temp):

        duty = (5.80 +
                0.21 * (ambient_temp)
                )
        return duty

    def GSHP_cop(self, flow_temp, ambient_temp):

        cop = (8.77 -
               0.15 * (flow_temp - ambient_temp) +
               0.000734 * (flow_temp - ambient_temp) ** 2
               )
        return cop

    def GSHP_duty(self, flow_temp, ambient_temp):

        duty = (9.37 +
                0.30 * ambient_temp
                )
        return duty

    def plot_cop(self):

        x_ambient = np.linspace(-5, 15, num=100)

        cop_55 = []
        for z in range(len(x_ambient)):
            c = self.ASHP_cop(55, x_ambient[z])
            if x_ambient[z] <= 5:
                c = 0.9 * c
            cop_55.append(c)

        cop_45 = []
        for z in range(len(x_ambient)):
            c = self.ASHP_cop(45, x_ambient[z])
            if x_ambient[z] <= 5:
                c = 0.9 * c
            cop_45.append(c)

        plt.plot(x_ambient, cop_45, LineWidth=2)
        plt.plot(x_ambient, cop_55, LineWidth=2)
        plt.legend(['Flow T 45', 'FLow T 55'], loc='best')
        plt.ylabel('COP')
        plt.xlabel('Ambient temperature')
        plt.show()


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

    def graphs(self):
        """OLD testing of how to do regression analysis

        includes input method, regression, graphing
        """

        path = t.inputs_path()
        file1 = os.path.join(path['folder_path'], "regression1.pkl")
        regression1 = pd.read_pickle(file1)

        path = t.inputs_path()
        file1a = os.path.join(path['folder_path'], "regression_temp1.pkl")
        regression_temp1 = pd.read_pickle(file1a)

        dic = {'flow_temp': [regression_temp1['flow_temp'][0],
                            regression_temp1['flow_temp'][0],
                            regression_temp1['flow_temp'][0],
                            regression_temp1['flow_temp'][0],
                            regression_temp1['flow_temp'][0],
                            regression_temp1['flow_temp'][0],
                            regression_temp1['flow_temp'][0],
                            regression_temp1['flow_temp'][0]]}
        df = pd.DataFrame(data=dic)
        data1 = pd.concat([regression1, df], axis=1)

        path = t.inputs_path()
        file2 = os.path.join(path['folder_path'], "regression2.pkl")
        regression2 = pd.read_pickle(file2)

        path = t.inputs_path()
        file2a = os.path.join(path['folder_path'], "regression_temp2.pkl")
        regression_temp2 = pd.read_pickle(file2a)

        dic2 ={'flow_temp': [regression_temp2['flow_temp'][0], 
                    regression_temp2['flow_temp'][0],
                    regression_temp2['flow_temp'][0],
                    regression_temp2['flow_temp'][0],
                    regression_temp2['flow_temp'][0],
                    regression_temp2['flow_temp'][0],
                    regression_temp2['flow_temp'][0],
                    regression_temp2['flow_temp'][0]]}
        df2 = pd.DataFrame(data=dic2)
        data2 = pd.concat([regression2, df2], axis=1)

        path = t.inputs_path()
        file3 = os.path.join(path['folder_path'], "regression3.pkl")
        regression3 = pd.read_pickle(file3)

        path = t.inputs_path()
        file3a = os.path.join(path['folder_path'], "regression_temp3.pkl")
        regression_temp3 = pd.read_pickle(file3a)

        dic3 ={'flow_temp': [regression_temp3['flow_temp'][0], 
                    regression_temp3['flow_temp'][0],
                    regression_temp3['flow_temp'][0],
                    regression_temp3['flow_temp'][0],
                    regression_temp3['flow_temp'][0],
                    regression_temp3['flow_temp'][0],
                    regression_temp3['flow_temp'][0],
                    regression_temp3['flow_temp'][0]]}
        df3 = pd.DataFrame(data=dic3)
        data3 = pd.concat([regression3, df3], axis=1)

        path = t.inputs_path()
        file4 = os.path.join(path['folder_path'], "regression4.pkl")
        regression4 = pd.read_pickle(file4)

        path = t.inputs_path()
        file4a = os.path.join(path['folder_path'], "regression_temp4.pkl")
        regression_temp4 = pd.read_pickle(file4a)

        dic4 ={'flow_temp': [regression_temp4['flow_temp'][0], 
                    regression_temp4['flow_temp'][0],
                    regression_temp4['flow_temp'][0],
                    regression_temp4['flow_temp'][0],
                    regression_temp4['flow_temp'][0],
                    regression_temp4['flow_temp'][0],
                    regression_temp4['flow_temp'][0],
                    regression_temp4['flow_temp'][0]]}
        df4 = pd.DataFrame(data=dic4)
        data4 = pd.concat([regression4, df4], axis=1)

        regression_data = data1.append([data2, data3, data4])
        regression_data = regression_data.dropna()
        regression_data = regression_data.reset_index(drop=True)

        #note that ambient temp is column1 and flow_temp is column 2
        X = regression_data.drop(columns=['duty', 'capacity_percentage', 'COSP'])

        Y_COSP = regression_data.drop(columns=['duty', 'capacity_percentage', 'flow_temp', 'ambient_temp'])
        Y_duty = regression_data.drop(columns=['COSP', 'capacity_percentage', 'flow_temp', 'ambient_temp'])

        poly = PolynomialFeatures(degree=2, include_bias=False)
        X_new = poly.fit_transform(X)
        Y_COSP_new = poly.fit_transform(Y_COSP)

        model_cop = LinearRegression()
        model_cop.fit(X_new, Y_COSP_new)

        model_duty = LinearRegression()
        model_duty.fit(X_new, Y_duty)

        x_ambient = np.linspace(-20,20,num=100)
        df1 = pd.DataFrame(data=x_ambient)

        x_flow_temp = np.array([50, 55, 60, 65, 70, 75, 80])
        df2 = pd.DataFrame(data=x_flow_temp)

        f_t = []
        am = []

        for x in range(0, len(x_flow_temp)):
            for y in range(0, len(x_ambient)):
                f_t.append(x_flow_temp[x])
                am.append(x_ambient[y])

        df3 = pd.DataFrame(data=f_t)
        df3 = df3.rename(columns= {0:'flow_temp'})

        df4 = pd.DataFrame(data=am)
        df4 = df4.rename(columns= {0:'ambient_temp'})

        x_test = pd.concat([df4, df3], axis=1)
        x_test_new = poly.fit_transform(x_test)

        pred_cop = model_cop.predict(x_test_new)
        pred_duty = model_duty.predict(x_test_new)

        fileout = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'heatpump', 'regression_analysis.pdf')
        pp = PdfPages(fileout)

        dfs = []
        for x in range(0, len(df2)):
            y1 = x * len(df1)
            y2 = (x+1) * len(df1)
            dfs.append(pred_cop[y1:y2])

        fig, ax = plt.subplots()

        for x in range(0, len(df2)):
            ax.plot(df1, dfs[x][:,0], label = df2[0][x])
        ax.legend(title = 'Flow temperatures')
        ax.scatter(X['ambient_temp'], Y_COSP['COSP'])
        plt.xlabel('Ambient temp')
        plt.ylabel('COSP')
        pp.savefig(bbox_inches='tight')

        dfs2 = []
        for x in range(0, len(df2)):
            y1 = x * len(df1)
            y2 = (x+1) * len(df1)
            dfs2.append(pred_duty[y1:y2])

        fig, ax = plt.subplots()

        for x in range(0, len(df2)):
            ax.plot(df1, dfs2[x][:,0], label = df2[0][x])
        ax.legend(title = 'Flow temperatures')
        ax.scatter(X['ambient_temp'], Y_duty['duty'])
        plt.xlabel('Ambient temp')
        plt.ylabel('duty (kW)')
        pp.savefig(bbox_inches='tight')

        pp.close()
        return
