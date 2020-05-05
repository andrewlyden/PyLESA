"""tools module

useful functions which are used throughout
"""

import pandas as pd

import cPickle as pickle
from collections import OrderedDict


def inputs_path():
    pickle_in = open("dic_path.pkl", "rb")
    dic = pickle.load(pickle_in)
    pickle_in.close()
    return dic


def month_split(year):

    month_list = OrderedDict(
        [('jan', year[0:744]),
         ('feb', year[744:1416]),
         ('mar', year[1416:2160]),
         ('apr', year[2160:2880]),
         ('may', year[2880:3624]),
         ('jun', year[3624:4344]),
         ('jul', year[4344:5088]),
         ('aug', year[5088:5832]),
         ('sep', year[5832:6552]),
         ('oct', year[6552:7296]),
         ('nov', year[7296:8016]),
         ('dec', year[8016:8760])])

    return month_list


def sum_monthly(year):

    month_list = OrderedDict(
        [('jan', year[0:744].sum() / 1000),
         ('feb', year[744:1416].sum() / 1000),
         ('mar', year[1416:2160].sum() / 1000),
         ('apr', year[2160:2880].sum() / 1000),
         ('may', year[2880:3624].sum() / 1000),
         ('jun', year[3624:4344].sum() / 1000),
         ('jul', year[4344:5088].sum() / 1000),
         ('aug', year[5088:5832].sum() / 1000),
         ('sep', year[5832:6552].sum() / 1000),
         ('oct', year[6552:7296].sum() / 1000),
         ('nov', year[7296:8016].sum() / 1000),
         ('dec', year[8016:8760].sum() / 1000)])

    return month_list


def mean_monthly(year):

    month_list = OrderedDict(
        [('jan', year[0:744].values.mean()),
         ('feb', year[744:1416].values.mean()),
         ('mar', year[1416:2160].values.mean()),
         ('apr', year[2160:2880].values.mean()),
         ('may', year[2880:3624].values.mean()),
         ('jun', year[3624:4344].values.mean()),
         ('jul', year[4344:5088].values.mean()),
         ('aug', year[5088:5832].values.mean()),
         ('sep', year[5832:6552].values.mean()),
         ('oct', year[6552:7296].values.mean()),
         ('nov', year[7296:8016].values.mean()),
         ('dec', year[8016:8760].values.mean())])

    return month_list


def sum_year(year):
    return year.values.sum()


def mean_year(year):
    return year.values.mean()


def timeindex():
    time = pd.date_range(start='2017-01-01', periods=8760, freq='H')
    return time


def name_error(variable):

    if variable is None:
        variable1 = 0
    else:
        variable1 = variable
    return variable1

class CheckFunctions(object):

    def __init__(self, renewable_generation, elec_demand,
                 heat_demand):
        self.renewable_generation = renewable_generation
        self.elec_demand = elec_demand
        self.heat_demand = heat_demand

    def electrical_surplus_deficit(self):

        """
        this looks at total renewable generation and total electrical demand
        works out the surplus and deficit
        looks every timestep for whole year

        RETURNS
        pdf: a dataframe containing the following
            match: RES - elec_demand
            deficit: where demand exceeds RES
            surplus: where RES exceeds demand
        """

        # sum of the wind turbines and PV
        total_renewables = self.renewable_generation
        electrical_demand = self.elec_demand

        # match by subtracting between the total renewables and elec_demand
        match = total_renewables - electrical_demand

        # create empty lists for the deficit and surplus
        deficit = []
        surplus = []
        RES_used = []

        # search for the whole year, h=8760
        # calculates the deficit or surplus at each timestep,
        # and produces two separate dataframes
        for x in range(0, 8760):

            RES_used.append(min(total_renewables[x], electrical_demand[x]))

            if match[x] <= 0.0:
                deficit.append(-1 * match[x])
                surplus.append(0.0)

            else:
                deficit.append(0.0)
                surplus.append(match[x])

        d = {'match': match, 'deficit': deficit,
             'surplus': surplus, 'RES_used': RES_used}
        pdf = pd.DataFrame(data=d)

        return pdf

    def heat_demand_check(self, timestep, heat_generated):

        """
        this is used to check if the heat demand has been met
        PARAMETERS
        timestep: a float/int of the timestep to be modelled
        heat_generated: the total heat generated up to that
        point in the flow diagram to be checked

        RETURNS
        boolean statement:
            TRUE if heat demand met
            FALSE if heat demand not met
        exits program and returns a printed error if too much heat generated

        """

        # get the heat demand
        heat_demand = self.heat_demand[timestep]
        # print heat_demand, 'heat_demand'

        # checks how much heat demand still needs to be met
        heat_met = round(heat_demand, 2) - round(heat_generated, 2)
        heat_met = round(heat_met, 1)

        # if zero then heat demand is met
        if heat_met == 0:
            return True
        # if > 0 then heat demand not met
        elif heat_met > 0:
            return False
        # if < 0 then too much heat generated for some reason, throw error
        # else:
            # print 'Error in heat generation: Too much heat generated'
            # raise SystemExit()

    def surplus_check(self, surplus, RES_used):

        """
        this is used to check if surplus exists at point in flow diagram

        PARAMATERS

        timestep: a float/int of the timestep to be modelled
        surplus: total surplus in the timestep
        RES_used: surplus used up to point in the flow diagram

        RETURNS

        boolean statement:
            TRUE if surplus exists
            FALSE if surplus doesnt exist
        exits program and returns a printed error if too much RES has been used

        """

        # calculates how much RES is leftover
        RES_leftover = round(surplus, 2) - round(RES_used, 2)
        RES_leftover = round(RES_leftover, 2)

        # if greater than zero then surplus leftover
        if RES_leftover > 0:
            return True
        # if zero then no surplus
        elif RES_leftover == 0.0:
            return False
        # if something else then error
        # else:
        #     print 'Error in RES usage: Too much RES used'
        #     # raise SystemExit()

    def deficit_check(self, deficit, elec_supplied):

        deficit_leftover = round(deficit, 2) - round(elec_supplied, 2)
        deficit_leftover = round(deficit_leftover, 2)

        # if greater than zero then surplus leftover
        if deficit_leftover > 0:
            return True
        # if zero then no surplus
        elif deficit_leftover == 0:
            return False
        # if something else then error
        # else:
        #     print 'Error in program: Deficit turned into surplus'
        #     # raise SystemExit()