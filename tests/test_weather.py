import pylesa.environment.weather as weather
import pylesa.io.inputs as inputs


def test_PV_weather():

    i = inputs.weather()
    PV_weather = weather.Weather(DHI=i['DHI'], GHI=i['GHI'], DNI=i['DNI'],
                                 wind_speed_10=i['wind_speed_10'],
                                 wind_speed_50=i['wind_speed_50'],
                                 roughness_length=i['roughness_length'],
                                 pressure=i['pressure'],
                                 air_temperature=i['air_temperature'],
                                 air_density=i['air_density'],
                                 water_temperature=i['water_temperature']).PV()
    print(PV_weather)


def wind_weather():

    i = inputs.weather()
    wind_weather = weather.Weather(
        wind_speed_10=i['wind_speed_10'],
        wind_speed_50=i['wind_speed_50'],
        roughness_length=i['roughness_length'],
        pressure=i['pressure'],
        air_temperature=i['air_temperature']).wind_turbine()
    print(wind_weather)


# wind_weather()
