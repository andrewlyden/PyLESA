import matplotlib.pyplot as plt
import numpy as np
import os

import renewables
import inputs

name = 'WWHC_FOC_WM.xlsx'
subname = 'hp_1000_ts_400000'
# name = 'WWHC.xlsx'
# subname = 'hp_1000_ts_50000'
myInputs = inputs.Inputs(name, subname)


def wind_user_test():

    input_windturbine = myInputs.windturbine_user()
    input_weather = myInputs.weather()

    myWindturbine = renewables.Windturbine(
        turbine_name=input_windturbine['turbine_name'],
        hub_height=input_windturbine['hub_height'],
        rotor_diameter=input_windturbine['rotor_diameter'],
        multiplier=input_windturbine['multiplier'],
        nominal_power=input_windturbine['nominal_power'],
        power_curve=input_windturbine['power_curve'],
        weather_input=input_weather)

    myWindturbine.multiplier = 1

    power = myWindturbine.user_power()
    plt.style.use('ggplot')
    plt.rcParams.update({'font.size': 12})
    plt.plot(power)
    plt.ylabel('Output (kW)')
    plt.xlabel('Hour of year')
    plt.show()


wind_user_test()


def wind_database_test():

    input_windturbine = myInputs.windturbine_database()
    input_weather = myInputs.weather()

    myWindturbine = renewables.Windturbine(
        turbine_name=input_windturbine['turbine_name'],
        hub_height=input_windturbine['hub_height'],
        rotor_diameter=input_windturbine['rotor_diameter'],
        multiplier=input_windturbine['multiplier'],
        weather_input=input_weather)

    myWindturbine.multiplier = 1
    power = myWindturbine.database_power()

    plt.style.use('ggplot')
    plt.rcParams.update({'font.size': 12})
    plt.plot(power)
    plt.ylabel('Output (kW)')
    plt.xlabel('Hour of year')
    plt.show()


wind_database_test()


def wind_farm_test():

    input_windturbine = myInputs.wind_farm()
    input_weather = myInputs.weather()

    myWindfarm = renewables.Windturbine(
        turbine_name=input_windturbine['turbine_name'],
        hub_height=input_windturbine['hub_height'],
        rotor_diameter=input_windturbine['rotor_diameter'],
        multiplier=input_windturbine['number_of_turbines'],
        wind_farm_efficiency=input_windturbine['efficiency'],
        weather_input=input_weather)

    power = myWindfarm.wind_farm_power()

    plt.style.use('ggplot')
    plt.rcParams.update({'font.size': 12})
    plt.plot(power)
    plt.ylabel('Output (kW)')
    plt.xlabel('Hour of year')
    plt.show()


wind_farm_test()


def PV_test():

    input_PV_model = myInputs.PV_model()
    input_weather = myInputs.weather()

    myPV = renewables.PV(
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

    plt.style.use('ggplot')
    plt.rcParams.update({'font.size': 12})
    plt.plot(power)
    plt.ylabel('PV output (kW)')
    plt.xlabel('Hour of year')
    plt.show()

    # file = os.path.join(
    #     os.path.dirname(__file__), "..", "data", 'PV_output.csv')
    # np.savetxt(file, power.values, delimiter=",", fmt='%.3e')
    print(power.max())
    print(power.sum())


PV_test()
