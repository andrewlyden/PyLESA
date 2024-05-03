import grid
import inputs

import matplotlib.pyplot as plt

plt.style.use('ggplot')
plt.rcParams.update({'font.size': 22})

name = 'west_whins_combined.xlsx'
subname = 'hp_14_ts_380'
myInputs = inputs.Inputs(name, subname)
grid_inputs = myInputs.grid()

export = grid_inputs['export']
tariff_choice = grid_inputs['tariff_choice']
balancing_mechanism = grid_inputs['balancing_mechanism']
grid_services = grid_inputs['grid_services']

variable_periods_year = grid_inputs['variable_periods_year']

premium = grid_inputs['wm_info']['premium']
maximum = grid_inputs['wm_info']['maximum']

lower_percent = grid_inputs['ppa_info']['lower_percent']
higher_percent = grid_inputs['ppa_info']['higher_percent']
lower_penalty = grid_inputs['ppa_info']['lower_penalty']
higher_discount = grid_inputs['ppa_info']['higher_discount']


def flatrate():

    fr = grid_inputs['flat_rates']
    myGrid = grid.Grid(
        name, subname,
        tariff_choice, balancing_mechanism, grid_services,
        flat_rate=fr)
    return myGrid.flat_rates_series()


def flatrate_wind():

    fr = grid_inputs['flat_rates']
    myGrid = grid.Grid(
        name, subname, export,
        tariff_choice, balancing_mechanism, grid_services,
        flat_rate=fr, lower_percent=lower_percent,
        higher_percent=higher_percent, higher_discount=higher_discount,
        lower_penalty=lower_penalty)
    return myGrid.flat_rates_wind()


def variableperiods():

    vp = grid_inputs['variable_periods']
    myGrid = grid.Grid(
        name, subname, export,
        tariff_choice, balancing_mechanism, grid_services,
        variable_periods=vp, variable_periods_year=variable_periods_year)
    return myGrid.variable_periods_series()


def variableperiods_wind():

    vp = grid_inputs['variable_periods']
    myGrid = grid.Grid(
        name, subname, export,
        tariff_choice, balancing_mechanism, grid_services,
        variable_periods=vp, variable_periods_year=variable_periods_year,
        lower_percent=lower_percent,
        higher_percent=higher_percent, higher_discount=higher_discount,
        lower_penalty=lower_penalty)
    return myGrid.variable_periods_wind()


def tou_wm():

    twm = grid_inputs['wholesale_market']
    myGrid = grid.Grid(
        name, subname, export,
        tariff_choice, balancing_mechanism, grid_services,
        wholesale_market=twm, premium=premium,
        maximum=maximum)
    return myGrid.tou_wm_series()


def tou_wm_wind():

    twm = grid_inputs['wholesale_market']
    myGrid = grid.Grid(
        name, subname, export,
        tariff_choice, balancing_mechanism, grid_services,
        wholesale_market=twm, premium=premium,
        maximum=maximum, lower_percent=lower_percent,
        higher_percent=higher_percent, higher_discount=higher_discount,
        lower_penalty=lower_penalty)
    return myGrid.tou_wm_wind_ppa()


def wind():

    twm = grid_inputs['wholesale_market']
    myGrid = grid.Grid(
        name, subname, export,
        tariff_choice, balancing_mechanism, grid_services,
        wholesale_market=twm, premium=premium,
        maximum=maximum, lower_percent=lower_percent,
        higher_percent=higher_percent, higher_discount=higher_discount,
        lower_penalty=lower_penalty)
    return myGrid.wind_farm_info()


def plot_traditional():

    fr = flatrate()
    vp = variableperiods()
    twm = tou_wm()

    timesteps = 72
    hour1 = 0
    hour2 = hour1 + timesteps
    plt.plot(fr[hour1:hour2], LineWidth=2)
    # plt.plot(vp[hour1:hour2], LineWidth=2)
    plt.plot(twm[hour1:hour2], LineWidth=2)
    plt.legend(['Flat rates', 'Time of use'], loc='best')
    plt.ylabel('Import costs')
    plt.xlabel('Time (h)')
    plt.show()

    # # Plot solution
    # t = 72
    # hour1 = 0
    # hour2 = hour1 + t
    # plt.figure()
    # plt.subplot(3, 1, 1)
    # plt.plot(t, fr[hour1:hour2], LineWidth=2)
    # plt.ylabel('Flat rates')
    # plt.subplot(3, 1, 2)
    # plt.plot(t, new_tou[hour1:hour2], LineWidth=2)
    # plt.legend(['wind_ppa', 'no_wind_ppa'], loc='best')
    # plt.ylabel('Prices pound/MWh')
    # plt.subplot(3, 1, 3)
    # plt.plot(t, new_tou[hour1:hour2], LineWidth=2)
    # plt.legend(['wind_ppa', 'no_wind_ppa'], loc='best')
    # plt.ylabel('Prices pound/MWh')
    # plt.xlabel('Time')
    # plt.show()


def plot_future():

    frw = flatrate_wind()
    vpw = variableperiods_wind()
    twmw = tou_wm_wind()

    # timesteps = 192
    # hour1 = 1932
    timesteps = 250
    hour1 = 1300
    hour2 = hour1 + timesteps

    w = wind()
    power = w['power']
    lb = [w['lower_band']] * timesteps
    ub = [w['higher_band']] * timesteps

    plt.figure()
    plt.subplot(2, 1, 1)
    plt.plot(power[hour1:hour2].values, 'r', LineWidth=2)
    plt.plot(lb, 'g', LineWidth=2)
    plt.plot(ub, 'b', LineWidth=2)
    plt.ylabel('Wind farm')
    plt.legend(['output', 'lb', 'ub'], loc='best')
    plt.subplot(2, 1, 2)
    plt.plot(frw[hour1:hour2], LineWidth=2)
    # plt.plot(vpw[hour1:hour2], LineWidth=2)
    # plt.plot(twmw[hour1:hour2], LineWidth=2)
    plt.legend(['Flat rates', 'Variable periods', 'Time of use'], loc='best')
    plt.ylabel('Import costs')
    plt.xlabel('Time (h)')
    plt.show()


def findhorn():

    vp = grid_inputs['variable_periods']
    myGrid = grid.Grid(
        name, subname, export,
        tariff_choice, balancing_mechanism, grid_services,
        variable_periods=vp, variable_periods_year=variable_periods_year)

    day_night = myGrid.findhorn_tariff()
    # print day_night


findhorn()
# plot_traditional()
# plot_future()

# flatrate()
# print flatrate_wind()
# variableperiods()
# variableperiods_wind()
# tou_wm()
# tou_wm_wind()
