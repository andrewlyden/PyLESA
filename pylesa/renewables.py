"""renewables module for using windpowerlib and pvlib

creates class objects for wind turbines and PV for modelling
additionally includes methods for analysis relating to modelling outputs
"""

import pandas as pd
import math
import os
import numpy as np

import pvlib
from pvlib.pvsystem import PVSystem
from pvlib.location import Location
from pvlib.modelchain import ModelChain

from windpowerlib.modelchain import ModelChain as ModelChain1
from windpowerlib.wind_turbine import WindTurbine

from windpowerlib.turbine_cluster_modelchain import TurbineClusterModelChain
from windpowerlib.wind_farm import WindFarm

from . import weather
from . import inputs

# # You can use the logging package to get
# # logging messages from the windpowerlib
# # Change the logging level if you want more or less messages
# import logging
# logging.getLogger().setLevel(logging.DEBUG)
np.seterr(invalid='ignore')

def sum_renewable_generation():

    tot = wind_user_power() + wind_database_power() + PV_power()
    return tot


def wind_user_power(name, subname):
    """power of user-defined wind turbine

    takes inputs from the excel spreadsheet
    creates a wind turbine object
    calculates hourly power output over year

    Returns:
        pandas df -- power output 8760 steps
    """
    myInputs = inputs.Inputs(name, subname)
    input_windturbine = myInputs.windturbine_user()
    input_weather = myInputs.weather()

    myWindturbine = Windturbine(
        turbine_name=input_windturbine['turbine_name'],
        hub_height=input_windturbine['hub_height'],
        rotor_diameter=input_windturbine['rotor_diameter'],
        multiplier=input_windturbine['multiplier'],
        nominal_power=input_windturbine['nominal_power'],
        power_curve=input_windturbine['power_curve'],
        weather_input=input_weather)

    power = myWindturbine.user_power()['wind_database']
    return power


def wind_database_power(name, subname):
    """power output for a wind turbine from database

    takes inputs for weather and wind turbine from database from excel

    Returns:
        pandas df -- power output of databased wind turbine
    """

    myInputs = inputs.Inputs(name, subname)
    input_windturbine = myInputs.windturbine_database()
    input_weather = myInputs.weather()

    myWindturbine = Windturbine(
        turbine_name=input_windturbine['turbine_name'],
        hub_height=input_windturbine['hub_height'],
        rotor_diameter=input_windturbine['rotor_diameter'],
        multiplier=input_windturbine['multiplier'],
        weather_input=input_weather)

    power = myWindturbine.database_power()['wind_user']
    return power


def PV_power(name, subname):
    """power output for PV

    takes inputs from excel sheet for weather and PV

    Returns:
        pandas df -- power output for year hourly for PV
    """

    myInputs = inputs.Inputs(name, subname)
    input_PV_model = myInputs.PV_model()
    input_weather = myInputs.weather()

    myPV = PV(
        module_name=input_PV_model['module_name'],
        inverter_name=input_PV_model['inverter_name'],
        multiplier=input_PV_model['multiplier'],
        surface_tilt=input_PV_model['surface_tilt'],
        surface_azimuth=input_PV_model['surface_azimuth'],
        surface_type=input_PV_model['surface_type'],
        loc_name=input_PV_model['loc_name'],
        latitude=input_PV_model['latitude'],
        longitude=input_PV_model['longitude'],
        altitude=input_PV_model['altitude'],
        weather_input=input_weather)

    power = myPV.power_output()
    return power


class PV(object):
    """PV class

    contains the attributes and methods for calculating PV power
    uses the PVlib library
    """

    def __init__(self, module_name, inverter_name, multiplier,
                 surface_tilt, surface_azimuth, surface_type,
                 loc_name, latitude, longitude, altitude, weather_input):
        """initialises instance of PV class

        Arguments:
            module_name {str} -- name of PV module from database
            inverter_name {str} -- name of inverter from database
            multiplier {int} -- number of PV systems
            surface_tilt {int} -- angle from horizontal
            surface_azimuth {int} -- angle in the horizontal plane
                                    measured from south
            surface_type {str} -- surrounding surface type
            loc_name {str} -- name of location
            latitude {int} -- latitude of location
            longitude {int} --
            altitude {int} --
            weather_input {dataframe} -- dataframe with PV weather inputs
        """

        # this replaces the whitespace or invalid characters
        # with underscores so it fits with PVlib calc
        module1 = module_name.replace(' ', '_').\
            replace('-', '_').replace('.', '_').\
            replace('(', '_').replace(')', '_').\
            replace('[', '_').replace(']', '_').\
            replace(':', '_').replace('+', '_').\
            replace('/', '_').replace('"', '_').\
            replace(',', '_')
        inverter1 = inverter_name.replace(' ', '_').\
            replace('-', '_').replace('.', '_').\
            replace('(', '_').replace(')', '_').\
            replace('[', '_').replace(']', '_').\
            replace(':', '_').replace('+', '_').\
            replace('/', '_').replace('"', '_').\
            replace(',', '_')

        cec_modules = pvlib.pvsystem.retrieve_sam('CECMod')
        sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')

        if module1 in cec_modules:
            self.module = cec_modules[module1]
        elif module1 in sandia_modules:
            self.module = sandia_modules[module1]
        else:
            raise Exception('Could not retrieve PV module data')

        # of inverters and returns a pandas df
        CEC_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
        # print(CEC_inverters)
        inverter1 = 'iPower__SHO_4_8__240V_'
        self.inverter = CEC_inverters[inverter1]

        # tech parameters
        self.multiplier = multiplier
        self.surface_tilt = surface_tilt
        self.surface_azimuth = surface_azimuth
        self.surface_type = surface_type

        # location parameters
        self.loc_name = loc_name
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude

        # weather inputs
        self.weather_input = weather_input

    def weather_data(self):
        """gets PV weather data

        gets weather data from the excel sheet for the PV

        Returns:
            df -- dhi, ghi, dni, wind_speed, temp_air
        """
        PV_weather = weather.Weather(
            DHI=self.weather_input['DHI'],
            GHI=self.weather_input['GHI'],
            DNI=self.weather_input['DNI'],
            wind_speed_10=self.weather_input['wind_speed_10'],
            air_temperature=self.weather_input['air_temperature']).PV()
        return PV_weather

    def power_output(self):
        """calculates the power output of PV

        Returns:
            df -- power output
        """

        if self.multiplier == 0:
            data = np.zeros(8760)
            df = pd.Series(data)
            return df

        location = Location(
            latitude=self.latitude, longitude=self.longitude)

        system = PVSystem(
            surface_tilt=self.surface_tilt,
            surface_azimuth=self.surface_azimuth,
            module_parameters=self.module,
            inverter_parameters=self.inverter)

        mc = ModelChain(
            system, location)
        weather = self.weather_data()

        weather.index = pd.date_range(
            start='01/01/2017', end='01/01/2018',
            freq='1h', tz='Europe/London', closed='left')
        # times = naive_times.tz_localize('Europe/London')
        # print weather
        # weather = pd.DataFrame(
        #     [[1050, 1000, 100, 30, 5]],
        #     columns=['ghi', 'dni', 'dhi', 'temp_air', 'wind_speed'],
        #     index=[pd.Timestamp('20170401 1200', tz='Europe/London')])

        mc.run_model(weather=weather)
        # multiply by system losses
        # also multiply by correction factor
        power = (mc.ac.fillna(value=0).round(2) *
                 self.multiplier * 0.001 * 0.85 * 0.85)
        # remove negative values
        power[power < 0] = 0
        # multiply by monthly correction factors
        # for correcting MEERA solar data set
        cf = [1.042785944,
              1.059859907,
              1.037299072,
              0.984286745,
              0.995849527,
              0.973795815,
              1.003315908,
              1.014427134,
              1.046833,
              1.091837017,
              1.039504694,
              0.95520793]

        # multiply by correction factor for each hour
        for hour in range(8760):
            month = int(math.floor(hour / 730))
            power[hour] = power[hour] * cf[month]

        power = power.reset_index(drop=True)

        return power


class Windturbine(object):

    def __init__(self, turbine_name, hub_height,
                 rotor_diameter, multiplier, weather_input,
                 nominal_power=None, power_curve=None,
                 wind_farm_efficiency=None):
        """wind turbine class

        class for modelling user and database defined equations

        Arguments:
            turbine_name {str} -- name of turbine, only matters for database
            hub_height {float} -- height of turbine
            rotor_diameter {float} --
            multiplier {int} -- number of wind turbines of type
            weather_input {pandas df} -- use weather class wind instance method

        Keyword Arguments (for user-defined turbine):
            nominal_power {float} -- (default: {None})
            power_curve {[dict ]} -- dict with power curve
                                     values (default: {None})
        """

        self.turbine_name = turbine_name
        self.hub_height = hub_height
        self.rotor_diameter = rotor_diameter
        self.multiplier = multiplier
        self.weather_input = weather_input

        self.nominal_power = nominal_power
        self.power_curve = power_curve
        self.wind_farm_efficiency = wind_farm_efficiency

    def weather_data(self):
        """input weather data

        creates weather object with necessary attributes

        Returns:
            pandas df -- hourly weather data for wind modelling
        """

        wind_weather = weather.Weather(
            wind_speed_10=self.weather_input['wind_speed_10'],
            wind_speed_50=self.weather_input['wind_speed_50'],
            roughness_length=self.weather_input['roughness_length'],
            pressure=self.weather_input['pressure'],
            air_temperature=self.weather_input['air_temperature']).wind_turbine()
        return wind_weather

    def user_power(self):
        """wind power output for user-defined turbine

        inputs weather and turbine spec
        initialises the wind turbine object
        runs model
        calculates power output

        Returns:
            pandas df -- hourly year power output
        """

        if self.multiplier == 0:
            data = np.zeros(8760)
            df = pd.DataFrame(data, columns=['wind_user'])
            return df

        multi = self.multiplier

        # this returns dict which contains all the info for the windturbine
        myTurbine = {'name': self.turbine_name,
                     'nominal_power': self.nominal_power,
                     'hub_height': self.hub_height,
                     'rotor_diameter': self.rotor_diameter,
                     'power_curve': self.power_curve
                     }

        # input weather data
        weather = self.weather_data()

        # initialises a wind turbine object using
        # the WindTurbine class from windpowerlib
        UserTurbine = WindTurbine(**myTurbine)
        mc_my_turbine = ModelChain1(UserTurbine).run_model(weather)

        # 1000 factor to make it into kW,
        # and the multi to give number of wind turbines
        # multiply by 0.5 to correct MEERA dataset if needed
        series = (mc_my_turbine.power_output * multi / 1000.).round(2)
        df = series.to_frame()
        df.columns = ['wind_user']
        df = df.reset_index(drop=True)

        return df

    def database_power(self):
        """wind turbine database power output

        power output calculation
        initialise ModelChain with default
        parameters and use run_model method
        to calculate power output

        Returns:
            pandas df -- hourly year of power output
        """

        if self.multiplier == 0:
            data = np.zeros(8760)
            df = pd.DataFrame(data, columns=['wind_database'])
            return df

        multi = self.multiplier

        # specification of wind turbine where
        # power coefficient curve and nominal
        # power is provided in an own csv file

        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "data", 'oedb')#, 'power_curves.csv')

        myTurbine = {
            'turbine_type': self.turbine_name,  # turbine type as in file
            'hub_height': self.hub_height,  # in m
            'rotor_diameter': self.rotor_diameter,  # in m
            'path': csv_path  # using power_curve csv
        }

        # own specifications for ModelChain setup
        modelchain_data = {
            'wind_speed_model': 'logarithmic',  # 'logarithmic' (default),
                                                # 'hellman' or
                                                # 'interpolation_extrapolation'
            'density_model': 'barometric',  # 'barometric' (default), 'ideal_gas' or
                                           # 'interpolation_extrapolation'
            'temperature_model': 'linear_gradient',  # 'linear_gradient' (def.) or
                                                     # 'interpolation_extrapolation'
            'power_output_model': 'power_curve',  # 'power_curve' (default) or
                                                  # 'power_coefficient_curve'
            'density_correction': False,  # False (default) or True
            'obstacle_height': 0,  # default: 0
            'hellman_exp': None}  # None (default) or None

        # initialise WindTurbine object
        turbineObj = WindTurbine(**myTurbine)

        weather = self.weather_data()

        mc_my_turbine = ModelChain1(turbineObj, **modelchain_data).run_model(weather)
        # write power output timeseries to WindTurbine object
        # divide by 1000 to keep in kW
        # multply by 0.5 for correcting reanalysis dataset
        series = (mc_my_turbine.power_output * multi * 0.5 / 1000).round(2)
        df = series.to_frame()
        df.columns = ['wind_database']
        df = df.reset_index(drop=True)

        return df

    def wind_farm_power(self):

        # specification of wind turbine where
        # power coefficient curve and nominal
        # power is provided in an own csv file

        if self.multiplier == 0:
            data = np.zeros(8760)
            df = pd.DataFrame(data, columns=['wind_farm'])
            return df

        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "data", 'oedb')
        myTurbine = {
            'turbine_type': self.turbine_name,  # turbine type as in file
            'hub_height': self.hub_height,  # in m
            'rotor_diameter': self.rotor_diameter,  # in m
            'path': csv_path  # using power_curve csv
        }

        # initialise WindTurbine object
        siemens = WindTurbine(**myTurbine)

        # specification of wind farm data
        farm = {
            'name': 'example_farm',
            'wind_turbine_fleet': [
                {'wind_turbine': siemens,
                 'number_of_turbines': self.multiplier}],
            'efficiency': self.wind_farm_efficiency}

        # initialize WindFarm object
        farm_obj = WindFarm(**farm)

        weather = self.weather_data()

        # power output calculation for example_farm
        # initialize TurbineClusterModelChain with default parameters and use
        # run_model method to calculate power output
        mc_farm = TurbineClusterModelChain(farm_obj).run_model(weather)
        # write power output time series to WindFarm object
        farm_obj.power_output = mc_farm.power_output

        # units in kWh
        # times by 0.5 to correct for MEERA dataset
        series = (farm_obj.power_output * 0.5 / 1000).round(2)
        df = series.to_frame()
        df.columns = ['wind_farm']

        return df
