"""grid module for generating electricity tariffs
"""

import os
import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt

import renewables
import inputs

plt.style.use('ggplot')


class Grid(object):

    def __init__(self, name, subname, export,
                 tariff_choice, balancing_mechanism, grid_services,
                 flat_rate=None, variable_periods=None,
                 variable_periods_year=None,
                 wholesale_market=None, bm_series=None, PPA_series=None,
                 grid_services_series=None, premium=None, maximum=None,
                 lower_percent=None, higher_percent=None,
                 lower_penalty=None, higher_discount=None):

        self.export = export
        self.name = name
        self.subname = subname
        self.tariff_choice = tariff_choice
        self.balancing_mechanism = balancing_mechanism
        self.grid_services = grid_services
        self.flat_rate = flat_rate
        self.variable_periods = variable_periods
        self.variable_periods_year = variable_periods_year
        self.wholesale_market = wholesale_market
        self.bm_series = bm_series
        self.PPA_series = PPA_series
        self.grid_services_series = grid_services_series
        self.premium = premium
        self.maximum = maximum
        self.lower_percent = lower_percent
        self.higher_percent = higher_percent
        self.lower_penalty = lower_penalty
        self.higher_discount = higher_discount

    def import_cost_series(self):

        if self.tariff_choice == 'Flat rates':
            return self.flat_rates_series()

        elif self.tariff_choice == 'Variable periods':
            return self.variable_periods_series()

        elif self.tariff_choice == 'Time of use - WM':
            return self.tou_wm_series()

        elif self.tariff_choice == 'Time of use - PPA + WM':
            return self.tou_wm_wind_ppa()

        elif self.tariff_choice == 'Time of use - PPA + FR':
            return self.flat_rates_wind()

        elif self.tariff_choice == 'Time of use - PPA + VP':
            return self.variable_periods_wind()

    def wind_farm_info(self):

        myInputs = inputs.Inputs(self.name, self.subname)
        input_windturbine = myInputs.wind_farm()
        input_weather = myInputs.wind_farm_weather()

        myWindfarm = renewables.Windturbine(
            turbine_name=input_windturbine['turbine_name'],
            hub_height=input_windturbine['hub_height'],
            rotor_diameter=input_windturbine['rotor_diameter'],
            multiplier=input_windturbine['number_of_turbines'],
            wind_farm_efficiency=input_windturbine['efficiency'],
            weather_input=input_weather)

        power = myWindfarm.wind_farm_power()['wind_farm']
        data = power.values
        sort = np.sort(data)[::-1]
        exceedence = np.arange(1., len(sort) + 1) / len(sort)
        exceedence_rounded = np.around(exceedence, decimals=2)

        lower_band_array = np.where(
            exceedence_rounded == self.lower_percent)[0]
        lower_band_array_median = np.median(lower_band_array)
        lower_band = sort[int(lower_band_array_median)]

        higher_band_array = np.where(
            exceedence_rounded == self.higher_percent)[0]
        higher_band_array_median = np.median(higher_band_array)
        higher_band = sort[int(higher_band_array_median)]

        dic = {'lower_band': lower_band, 'higher_band': higher_band,
               'power': power}

        return dic

    def flat_rates_series(self):

        import_cost = self.flat_rate['import']
        ic = np.empty(8760)
        for t in range(8760):
            ic[t] = import_cost
        return ic

    def flat_rates_wind(self):

        fr = self.flat_rates_series()

        wind_farm = self.wind_farm_info()
        higher_band = wind_farm['higher_band']
        lower_band = wind_farm['lower_band']
        power = wind_farm['power']

        new_tou = np.empty(8760)
        diff_tou = np.empty(8760)
        for t in range(8760):
            if power[t] >= higher_band:
                new_tou[t] = fr[t] - self.higher_discount
            elif power[t] <= lower_band:
                new_tou[t] = fr[t] + self.lower_penalty
            else:
                new_tou[t] = fr[t]
            diff_tou[t] = new_tou[t] - fr[t]

        # plt.plot(diff_tou)
        # plt.show()

        hour1 = 1930
        hour2 = 2026

        lb = []
        for x in range(hour2 - hour1):
            lb.append(lower_band)
        ub = []
        for x in range(hour2 - hour1):
            ub.append(higher_band)

        # # Plot solution
        # t = range(hour2 - hour1)
        # plt.figure()
        # plt.subplot(2, 1, 1)
        # plt.plot(t, power[hour1:hour2].values, 'r', LineWidth=2)
        # plt.plot(t, lb, 'g', LineWidth=2)
        # plt.plot(t, ub, 'b', LineWidth=2)
        # plt.ylabel('Wind farm')
        # plt.legend(['output', 'lb', 'ub'], loc='best')
        # plt.subplot(2, 1, 2)
        # plt.plot(t, new_tou[hour1:hour2], 'r', LineWidth=2)
        # plt.plot(t, fr[hour1:hour2], 'g', LineWidth=2)
        # plt.legend(['wind_ppa', 'no_wind_ppa'], loc='best')
        # plt.ylabel('Prices pound/MWh')
        # plt.xlabel('Time')
        # plt.show()

        return new_tou

    def variable_periods_series(self):

        year = self.variable_periods_year
        # first day of year
        day_list = []
        for day in range(1, 8):
            a = datetime.datetime(year, 1, day)
            day_list.append(a.strftime("%A"))
        z = datetime.datetime(year, 12, 31)
        last_day = z.strftime("%A")

        variable_periods_cost = self.variable_periods

        vpc = []
        for week in range(52):
            for day in range(7):
                for hour in range(24):
                    vpc.append(variable_periods_cost[day_list[day]][hour])
        for hour in range(24):
            vpc.append(variable_periods_cost[last_day][hour])

        # plt.plot(vpc[1930:2026], LineWidth=2)
        # plt.ylabel('Import cost (pound/MWh)')
        # plt.xlabel('Time (h)')
        # plt.show()
        return vpc

    def variable_periods_wind(self):

        vp = self.variable_periods_series()

        wind_farm = self.wind_farm_info()
        higher_band = wind_farm['higher_band']
        lower_band = wind_farm['lower_band']
        power = wind_farm['power']

        new_tou = np.empty(8760)
        diff_tou = np.empty(8760)
        for t in range(8760):
            if power[t] >= higher_band:
                new_tou[t] = vp[t] - self.higher_discount
            elif power[t] <= lower_band:
                new_tou[t] = vp[t] + self.lower_penalty
            else:
                new_tou[t] = vp[t]
            diff_tou[t] = new_tou[t] - vp[t]

        # plt.plot(diff_tou)
        # plt.show()

        hour1 = 1930
        hour2 = 2026

        lb = []
        for x in range(hour2 - hour1):
            lb.append(lower_band)
        ub = []
        for x in range(hour2 - hour1):
            ub.append(higher_band)

        # Plot solution
        # t = range(hour2 - hour1)
        # plt.figure()
        # plt.subplot(2, 1, 1)
        # plt.plot(t, power[hour1:hour2].values, 'r', LineWidth=2)
        # plt.plot(t, lb, 'g', LineWidth=2)
        # plt.plot(t, ub, 'b', LineWidth=2)
        # plt.ylabel('Wind farm')
        # plt.legend(['output', 'lb', 'ub'], loc='best')
        # plt.subplot(2, 1, 2)
        # plt.plot(t, new_tou[hour1:hour2], 'r', LineWidth=2)
        # plt.plot(t, vp[hour1:hour2], 'g', LineWidth=2)
        # plt.legend(['wind_ppa', 'no_wind_ppa'], loc='best')
        # plt.ylabel('Prices pound/MWh')
        # plt.xlabel('Time')
        # plt.show()

        return new_tou

    def tou_wm_series(self):

        wm = self.wholesale_market['wholesale_market']

        tou_wm = []
        for day in range(365):
            for hour in range(24):
                # premium between 4pm and 7pm
                current_hour = hour + day * 24
                if hour == 16 or hour == 17 or hour == 18:
                    tou_wm.append(
                        min(2.2 * wm[current_hour] +
                            self.premium, self.maximum))
                else:
                    tou_wm.append(
                        min(2.2 * wm[current_hour], self.maximum))
        # plt.plot(tou_wm[:72])
        # plt.plot(wm[:72])
        # plt.show()
        return tou_wm

    def tou_wm_wind_ppa(self):

        wind_farm = self.wind_farm_info()
        higher_band = wind_farm['higher_band']
        lower_band = wind_farm['lower_band']
        power = wind_farm['power']

        # get tou from tou_wm_series
        tou = self.tou_wm_series()

        new_tou = np.empty(8760)
        diff_tou = np.empty(8760)
        for t in range(8760):
            if power[t] >= higher_band:
                new_tou[t] = tou[t] - self.higher_discount
            elif power[t] <= lower_band:
                new_tou[t] = tou[t] + self.lower_penalty
            else:
                new_tou[t] = tou[t]
            diff_tou[t] = new_tou[t] - tou[t]
        # plt.plot(diff_tou)
        # plt.show()

        hour1 = 1930
        hour2 = 2000

        lb = []
        for x in range(hour2 - hour1):
            lb.append(lower_band)
        ub = []
        for x in range(hour2 - hour1):
            ub.append(higher_band)

        # # Plot solution
        # t = range(hour2 - hour1)
        # plt.figure()
        # plt.subplot(2, 1, 1)
        # plt.plot(t, power[hour1:hour2].values, 'r', LineWidth=2)
        # plt.plot(t, lb, 'g', LineWidth=2)
        # plt.plot(t, ub, 'b', LineWidth=2)
        # plt.ylabel('Wind farm')
        # plt.legend(['output', 'lb', 'ub'], loc='best')
        # plt.subplot(2, 1, 2)
        # plt.plot(t, new_tou[hour1:hour2], 'r', LineWidth=2)
        # plt.plot(t, tou[hour1:hour2], 'g', LineWidth=2)
        # plt.legend(['wind_ppa', 'no_wind_ppa'], loc='best')
        # plt.ylabel('Prices pound/MWh')
        # plt.xlabel('Time')
        # plt.show()

        return new_tou

    def findhorn_tariff(self):

        # use variable period tariff but
        # if site export is above certain level
        # then drop price to 30
        vp = self.variable_periods_series()

        # read in csv
        file = os.path.join(
            os.path.dirname(__file__), "..", "data",
            "FindImEx.csv")
        df = pd.read_csv(file, header=None, names=['import', 'export'])
        net = df['export'] - df['import']

        band = 50

        new_tou = np.empty(8760)
        for t in range(8760):
            if net[t] >= band:
                new_tou[t] = 30
            else:
                new_tou[t] = vp[t]

        plt.plot(new_tou)
        plt.show()
