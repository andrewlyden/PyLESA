"""weather module

this is the analysis of the weather data
"""

import pandas as pd
import tools as t
import numpy as np


class Weather(object):

    def __init__(self, DHI=None, GHI=None, DNI=None,
                 wind_speed_10=None, wind_speed_50=None,
                 roughness_length=None, pressure=None,
                 air_temperature=None, air_density=None,
                 water_temperature=None):

        self.DHI = DHI
        self.GHI = GHI
        self.DNI = DNI
        self.wind_speed_10 = wind_speed_10
        self.wind_speed_50 = wind_speed_50
        self.roughness_length = roughness_length
        self.pressure = pressure
        self.air_temperature = air_temperature
        self.air_density = air_density
        self.water_temperature = water_temperature

    def PV(self):

        PV_weather = pd.concat([self.DHI, self.GHI,
                                self.DNI, self.wind_speed_10,
                                self.air_temperature],
                               axis=1)

        PV_weather = PV_weather.rename(
            columns={'DHI': 'dhi',
                     'GHI': 'ghi',
                     'DNI': 'dni'})
        PV_weather = PV_weather.dropna(axis='columns')
        PV_weather.index = t.timeindex()

        return PV_weather

    def wind_turbine(self):

        # wind_weather = pd.DataFrame([])
        data = {'wind1': self.wind_speed_10['wind_speed_10'].tolist(),
                'air': self.air_temperature['air_temperature'].tolist(),
                'pres': self.pressure['pressure'].tolist(),
                'rou': self.roughness_length['roughness_length'].tolist(),
                'wind2': self.wind_speed_50['wind_speed_50'].tolist()}

        weather_df = pd.DataFrame(data)

        weather_df.index = pd.date_range('1/1/2012',
                                         periods=8760,
                                         freq='H')
        weather_df.columns = [np.array(['wind_speed',
                                        'temperature',
                                        'pressure',
                                        'roughness_length',
                                        'wind_speed']),
                              np.array([10, 10, 0, 10, 50])]
        weather_df = weather_df.dropna(axis=1, how='all')

        return weather_df

    def heatpump(self):

        HP_resource = pd.concat([self.air_temperature,
                                 self.water_temperature],
                                axis=1)
        HP_resource.index = t.timeindex()

        return HP_resource

    def hot_water_tank(self):

        return self.air_temperature
