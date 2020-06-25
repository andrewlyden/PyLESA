"""auxiliary modules

contains class for auxiliaries which covers
back up heaters
"""

import inputs


def aux_outputs(demand):
    """aux outputs

    takes inputs from excel sheet
    creates aux class object
    calculates demand, fuel usage in kwh, fuel mass in kg, and cost

    Arguments:
        demand {float} -- given demand to be met by aux

    Returns:
        dict -- demand, fuel usage and cost
    """

    i = inputs.aux()

    myAux = Aux(
        i['fuel'],
        i['efficiency'],
        i['fuel_info'])

    dem = myAux.demand_calc(demand)
    usage = myAux.fuel_usage(demand)

    outputs = {'dem': dem, 'usage': usage}

    return outputs


class Aux(object):

    def __init__(self, fuel, efficiency, fuel_info):
        """class instance

        Arguments:
            fuel {str} -- name of fuel used
            efficiency {float} -- efficiency of fuel transform
        """

        self.fuel = fuel
        self.efficiency = efficiency
        if fuel == 'Electric':
            pass
        else:
            self.cost = fuel_info[fuel]['cost']
            self.energy_density = fuel_info[fuel]['energy_density']

    def demand_calc(self, demand):
        """energy demand met by fuel transformer

        Arguments:
            demand {float} -- unmet demand

        Returns:
            float -- demand met by fuel transformer
        """

        return demand

    def fuel_usage(self, demand):
        """fuel used in kWh

        Arguments:
            demand {float} -- unmet demand

        Returns:
            float -- fuel used in kWh
        """

        fuel_usage = demand / self.efficiency

        return fuel_usage
