"""modelling hot watertanks

lowest capacity is 100L, this can be used as
"no" thermal storage simulation as long as demand is large
"""
import logging
import os
import pandas as pd
import math

from scipy.integrate import odeint

from ..environment import weather

LOG = logging.getLogger(__name__)

INSULATION_k = {
    'polyurethane': 0.025,
    'fibreglass': 0.04,
    'polystyrene': 0.035
}
INSIDE = 'Inside'
OUTSIDE = 'Outside'

class HotWaterTank(object):

    def __init__(self, capacity, insulation, location, number_nodes,
                 dimensions, tank_openings, correction_factors,
                 air_temperature=None):
        """hot water tank class object

        Arguments:
            capacity {float} -- capacity in L of tank
            insulation {str} -- type of insulation of tank
            location {str} -- outside or inside
            number_nodes {int} -- number of nodes
            dimensions {dict} -- {height, width, insul thickness}
            tank_openings {dict} -- {'tank_opening'
                                    'tank_opening_diameter'
                                    'uninsulated_connections'
                                    'uninsulated_connections_diameter'
                                    'insulated_connections'
                                    'insulated_connections_diameter'}
            correction_factors {dict} -- insulation factor and overall factor

        Keyword Arguments:
            air_temperature {dataframe} -- (default: {None})
        """

        # float or str inputs
        self.capacity = capacity
        self.insulation = insulation
        self.location = location
        self.number_nodes = number_nodes

        # dic inputs
        self.dimensions = dimensions
        # using new calc for dimensions
        # assuming a ratio of height to width of 2.5
        factor = 2.5
        self.dimensions['width'] = 2 * (self.capacity / (factor * math.pi)) ** (1. / 3)
        self.dimensions['height'] = 0.5 * factor * self.dimensions['width']
        # assuming a ratio of width to insulation thickness
        ins_divider = 8
        self.dimensions['insulation_thickness'] = self.dimensions['width'] / ins_divider

        self.tank_openings = tank_openings
        self.correction_factors = correction_factors

        # optional input, needed if location is set to outside
        self.air_temperature = air_temperature

        file = os.path.join(os.path.dirname(__file__),
                            "..",
                            "data",
                            'water_spec_heat.pkl')
        df = pd.read_pickle(file)
        self.cp_spec = df

    def init_temps(self, initial_temp):
        nodes_temp = []
        for node in range(self.number_nodes):
            nodes_temp.append(initial_temp)
        return nodes_temp

    def calc_node_mass(self):
        """calculates the mass of one node

        Returns:
            float -- mass of one node kg
        """

        node_mass = float(self.capacity) / self.number_nodes
        return node_mass

    def insulation_k_value(self):
        """selects k for insulation

        Returns:
            float -- k-value of insulation W/mK
        """
        if not self.insulation in INSULATION_k:
            msg = f'Insulation {self.insulation} is not valid, must be one of {INSULATION_k}'
            LOG.error(msg)
            raise ValueError(msg)

        # units of k need to be adjusted from W to joules
        # over the hour, and this requires
        # minuts in hour * seconds in minute (60*60)
        return INSULATION_k[self.insulation.lower()] * 3600

    def specific_heat_water(self, temp):
        """cp of water

        Arguments:
            temp {float} -- temperature of water

        Returns:
            float -- cp of water at given temp - j/(kg deg C)
        """
        # input temp must be between 0 and 100 deg

        if isinstance(temp, (int, float)) and temp > 0.:

            df = self.cp_spec
            T = round(float(temp), -1)
            # convert j/g deg to j/kg deg
            cp = df['Cp'][T / 10] * 1000

        else:
            cp = 4180

        return cp

    def internal_radius(self):
        """calculates internal radius

        Returns:
            float -- internal radius, m
        """

        r1 = self.dimensions['width'] - self.dimensions['insulation_thickness']
        return r1

    def amb_temp(self, timestep):
        """ambient temperature surrounding tank

        If location of storage is inside then a 15 deg ambient
        condition is assumed else if location is outside then
        outdoor temperature is used.

        Arguments:
            timestep {int} --

        Returns:
            float -- ambient temp surrounding tank degC
        """
        if self.location == OUTSIDE:

            w = weather.Weather(
                air_temperature=self.air_temperature).hot_water_tank()
            ambient_temp = w['air_temperature']['air_temperature'][timestep]

        elif self.location == INSIDE:
            ambient_temp = 15.0

        else:
            msg = f'Location {self.location} not valid, must be one of [{INSIDE}, {OUTSIDE}]'
            LOG.error(msg)
            raise ValueError(msg)
        return ambient_temp

    def discharging_function(self, state, nodes_temp, flow_temp):

        # total nodes is the number of nodes being modelled
        # nodes_temp is a dict of the nodes and their temperatures
        # return_temp is the temperature from the scheme going
        # back into the storage

        total_nodes = self.number_nodes
        node_list = range(total_nodes)
        function = {}
        # bottom_node = total_nodes - 1

        if state == 'discharging':

            for node in node_list:

                # this asks if we are looking at the top node
                # and if the charging water is above this nodes temp
                if node == 0 and flow_temp <= nodes_temp[0]:
                    function[node] = 1

                # if the source temp is lower than
                elif node == 0 and flow_temp >= nodes_temp[0]:
                    function[node] = 0

                # top node then goes in other node
                elif flow_temp < nodes_temp[node] and flow_temp >= nodes_temp[node - 1]:
                    function[node] = 1

                # for out of bounds nodes, shouldnt occur
                elif node < 0 or node == total_nodes + 1:
                    function[node] = 0

                else:
                    function[node] = 0

        elif state == 'charging' or state == 'standby':
            for node in node_list:
                function[node] = 0

        return function

    def discharging_bottom_node(self, state, nodes_temp,
                                return_temp, flow_temp):

        total_nodes = self.number_nodes
        node_list = range(total_nodes)
        function = {}
        bottom_node = total_nodes - 1

        df = self.discharging_function(state, nodes_temp, flow_temp)
        df_list = []
        for i in range(total_nodes):
            df_list.append(df[i])

        if 1 in df_list:

            for node in node_list:

                # this asks if we are looking at the bottom node
                if node == bottom_node and nodes_temp[0] >= flow_temp:
                    function[node] = 1

                elif node == bottom_node and nodes_temp[0] < flow_temp:
                    function[node] = 0

                else:
                    function[node] = 0

        else:
            for node in node_list:
                function[node] = 0

        return function

    def charging_function(self, state, nodes_temp, source_temp):

        # this determines which node recieves the charging water

        # total nodes is the number of nodes being modelled
        # nodes_temp is a dict of the nodes and their temperatures
        # source_temp is the temperature from the source going into the storage

        # if the in mass exceeds the node volume then next node also charged

        total_nodes = self.number_nodes
        node_list = range(total_nodes)
        function = {}
        if state == 'charging':

            for node in node_list:

                # this asks if we are looking at the top node
                # and if the charging water is above this nodes temp
                if node == 0 and source_temp >= nodes_temp[0]:
                    function[node] = 1

                # if the source temp is lower than
                elif node == 0 and source_temp <= nodes_temp[0]:
                    function[node] = 0

                # top node then goes in other node
                elif source_temp >= nodes_temp[node] and source_temp <= nodes_temp[node - 1]:
                    function[node] = 1

                # for out of bounds nodes, shouldnt occur
                elif node < 0 or node == total_nodes + 1:
                    function[node] = 0

                else:
                    function[node] = 0

        elif state == 'discharging' or 'standby':
            for node in node_list:
                function[node] = 0
        return function

    def charging_top_node(self, state):

        function = {}
        for node in range(self.number_nodes):

            if state == 'charging' and node == self.number_nodes - 1:
                function[node] = 1
            else:
                function[node] = 0

        return function

    def mixing_function(self, state, node, nodes_temp,
                        source_temp, flow_temp):

        total_nodes = self.number_nodes
        bottom_node = total_nodes - 1

        cf = self.charging_function(state, nodes_temp, source_temp)
        cf_list = []
        for i in range(total_nodes):
            cf_list.append(cf[i])

        df = self.discharging_function(state, nodes_temp, flow_temp)
        df_list = []
        for i in range(total_nodes):
            df_list.append(df[i])

        mf = {}

        if 1 in cf_list:
            for n in range(self.number_nodes):
                if cf[n] == 1:
                    node_charging = n
        else:
            node_charging = bottom_node + 1
        if 1 in df_list:
            for n in range(self.number_nodes):
                if df[n] == 1:
                    node_discharging = n
        else:
            node_discharging = bottom_node + 1

        if state == 'charging':
            if node <= node_charging:
                mf['Fcnt'] = 0
                mf['Fdnt'] = 0
            else:
                mf['Fcnt'] = 1
                mf['Fdnt'] = 0

            if node == bottom_node or node < node_charging:
                mf['Fcnb'] = 0
                mf['Fdnb'] = 0
            else:
                mf['Fcnb'] = 1
                mf['Fdnb'] = 0
        # discharging
        elif state == 'discharging':
            if node == 0 or node <= node_discharging:
                mf['Fcnt'] = 0
                mf['Fdnt'] = 0
            else:
                mf['Fcnt'] = 0
                mf['Fdnt'] = 1

            if node == bottom_node or node < node_discharging:
                mf['Fcnb'] = 0
                mf['Fdnb'] = 0
            else:
                mf['Fcnb'] = 0
                mf['Fdnb'] = 1
        # standby
        else:
                mf['Fcnt'] = 0
                mf['Fdnt'] = 0
                mf['Fcnb'] = 0
                mf['Fdnb'] = 0

        return mf

    def connection_losses(self):

        tank_opening = self.tank_openings[
            'tank_opening']
        tank_opening_d = self.tank_openings[
            'tank_opening_diameter']
        uninsulated_connections = self.tank_openings[
            'uninsulated_connections']
        uninsulated_connections_d = self.tank_openings[
            'uninsulated_connections_diameter']
        insulated_connections = self.tank_openings[
            'insulated_connections']
        insulated_connections_d = self.tank_openings[
            'insulated_connections_diameter']

        # divided by 0.024 to convert from kWh/day to W
        tank_opening_loss = (
            ((tank_opening_d * 0.001) ** 2) *
            math.pi * tank_opening * 27 / (4 * 0.024))

        uninsulated_connections_loss = (
            uninsulated_connections_d * 0.001 *
            uninsulated_connections * 5 / 0.024)

        insulated_connections_loss = (
            insulated_connections_d * 0.001 *
            insulated_connections * 3.5 / 0.024)

        loss = 3600 * (
            tank_opening_loss +
            uninsulated_connections_loss +
            insulated_connections_loss)

        return loss

    def DH_flow_post_mix(self, demand, flow_temp, return_temp):

        cp1 = self.specific_heat_water(flow_temp) / 1000.0
        mass_DH_flow = demand / (
            cp1 * (flow_temp - return_temp))
        return mass_DH_flow

    def source_out_pre_mix(self, thermal_output, source_temp, source_delta_t):

        cp1 = self.specific_heat_water(source_temp) / 1000.0
        mass_out_pre_mix = thermal_output / (
            cp1 * source_delta_t)
        return mass_out_pre_mix

    def thermal_storage_mass_charging(self, thermal_output, source_temp,
                                      source_delta_t, return_temp, flow_temp,
                                      demand, temp_tank_bottom):

        ts_mass = ((self.source_out_pre_mix(
            thermal_output, source_temp, source_delta_t) *
            source_delta_t -
            self.DH_flow_post_mix(demand, flow_temp, return_temp) *
            (flow_temp - return_temp)) /
            (source_temp - temp_tank_bottom))
        return ts_mass

    def thermal_storage_mass_discharging(self, thermal_output, source_temp,
                                         source_delta_t, return_temp,
                                         flow_temp,
                                         demand, temp_tank_top):

        # mass discharged in every tank timestep
        ts_mass = ((self.DH_flow_post_mix(demand, flow_temp, return_temp) *
                   (flow_temp - return_temp) -
                    self.source_out_pre_mix(
                        thermal_output, source_temp, source_delta_t) *
                   (source_delta_t)) /
                   (temp_tank_top - return_temp))
        return abs(ts_mass)

    def mass_flow_calc(self, state, flow_temp, return_temp,
                       source_temp, source_delta_t, thermal_output, demand,
                       temp_tank_bottom, temp_tank_top):
        if state == 'charging':
            # max_mass_flow_cha = self.mass_flow_to_charge(
            #     nodes_temp, source_temp,
            #     flow_temp, return_temp, timestep)
            mass_ts = self.thermal_storage_mass_charging(
                thermal_output, source_temp,
                source_delta_t, return_temp, flow_temp,
                demand, temp_tank_bottom)
            # if mass >= max_mass_flow_cha:
            #     mass_ts = max_mass_flow_cha
            # elif mass < max_mass_flow_cha:
            #     mass_ts = mass

        elif state == 'discharging':
            # max_mass_flow_dis = self.mass_flow_to_discharge(
            #     nodes_temp, source_temp,
            #     flow_temp, return_temp, timestep)
            mass_ts = self.thermal_storage_mass_discharging(
                thermal_output, source_temp, source_delta_t,
                return_temp, flow_temp, demand, temp_tank_top)
            # if mass >= max_mass_flow_dis:
            #     mass_ts = max_mass_flow_dis
            # elif mass < max_mass_flow_dis:
            #     mass_ts = mass
        elif state == 'standby':
            mass_ts = 0

        return mass_ts

    def coefficient_A(self, state, node, nodes_temp, mass_flow,
                      source_temp, flow_temp):
        node_mass = self.calc_node_mass()

        # specific heat at temperature of node i
        cp = self.specific_heat_water(nodes_temp[node])

        # thermal conductivity of insulation material
        k = self.insulation_k_value()

        # dimensions
        r1 = self.internal_radius()
        r2 = self.dimensions['width']
        h = self.dimensions['height']

        # correction factors
        Fi = self.correction_factors['insulation_factor']
        Fe = self.correction_factors['overall_factor']
        Fd = self.discharging_function(state, nodes_temp, flow_temp)[node]
        mf = self.mixing_function(state, node, nodes_temp,
                                  source_temp, flow_temp)
        Fco = self.charging_top_node(state)[node]

        A = (- Fd * mass_flow * cp -
             mf['Fdnt'] * mass_flow * cp -
             mf['Fcnb'] * mass_flow * cp -
             Fco * mass_flow * cp -
             Fe * Fi * k * ((1) / (r2 - r1)) *
             math.pi * ((r1 ** 2) + h * (r2 + r1))
             ) / (node_mass * cp)

        return A

    def coefficient_B(self, state, node, nodes_temp, mass_flow, source_temp,
                      flow_temp):

        node_mass = self.calc_node_mass()
        mf = self.mixing_function(state, node, nodes_temp,
                                  source_temp, flow_temp)

        B = mf['Fcnt'] * mass_flow / node_mass

        return B

    def coefficient_C(self, state, node, nodes_temp, mass_flow, source_temp,
                      flow_temp):
        node_mass = self.calc_node_mass()
        mf = self.mixing_function(state, node, nodes_temp,
                                  source_temp, flow_temp)

        C = mf['Fdnb'] * mass_flow / node_mass
        return C

    def coefficient_D(self, state, node, nodes_temp, mass_flow, source_temp,
                      flow_temp, return_temp, timestep):

        node_mass = self.calc_node_mass()

        # specific heat at temperature of node i
        cp = self.specific_heat_water(nodes_temp[node])

        # thermal conductivity of insulation material
        k = self.insulation_k_value()

        # dimensions
        r1 = self.internal_radius()
        r2 = self.dimensions['width']
        h = self.dimensions['height']

        # correction factors
        Fi = self.correction_factors['insulation_factor']
        Fe = self.correction_factors['overall_factor']

        Fc = self.charging_function(state, nodes_temp, source_temp)[node]
        Fdi = self.discharging_bottom_node(
            state, nodes_temp, return_temp, flow_temp)[node]
        Ta = self.amb_temp(timestep)

        cl = self.connection_losses()

        D = (Fc * mass_flow * cp * source_temp +
             Fdi * mass_flow * cp * return_temp +
             Fe * Fi * k * ((Ta) / (r2 - r1)) * math.pi *
             ((r1 ** 2) + h * (r2 + r1)) + Fe * cl
             ) / (node_mass * cp)

        return D

    def set_of_coefficients(self, state, nodes_temp, source_temp,
                            source_delta_t, flow_temp, return_temp,
                            thermal_output, demand, temp_tank_bottom,
                            temp_tank_top, timestep):

        mass_flow1 = self.mass_flow_calc(
            state, flow_temp, return_temp, source_temp, source_delta_t,
            thermal_output, demand, temp_tank_bottom, temp_tank_top)
        # errors may lead to slight overestimation of maximum mass flow
        # this accounts for this and ensures not going over node mass
        mass_flow = min(mass_flow1, self.calc_node_mass())

        c = []
        for node in range(self.number_nodes):
            coefficients = {'A': self.coefficient_A(
                state, node, nodes_temp, mass_flow, source_temp, flow_temp),
                            'B': self.coefficient_B(
                state, node, nodes_temp, mass_flow, source_temp, flow_temp),
                            'C': self.coefficient_C(
                state, node, nodes_temp, mass_flow, source_temp, flow_temp),
                            'D': self.coefficient_D(
                state, node, nodes_temp, mass_flow, source_temp, flow_temp,
                return_temp, timestep)}
            c.append(coefficients)
        return c

    def new_nodes_temp(self, state, nodes_temp, source_temp,
                       source_delta_t, flow_temp, return_temp,
                       thermal_output, demand, timestep):
        if self.capacity == 0:
            return nodes_temp

        check = 0.0
        for node in range(len(nodes_temp)):
            check += nodes_temp[node]
        if check == source_temp * len(nodes_temp) and state == 'charging':
            return nodes_temp * len(nodes_temp)

        def model_temp(z, t, c):
            dzdt = []
            for node in range(self.number_nodes):

                if node == 0:
                    Ti = nodes_temp[node]
                    Ti_b = nodes_temp[node + 1]

                    dTdt = (c[node]['A'] * Ti +
                            c[node]['C'] * Ti_b +
                            c[node]['D'])

                    dzdt.append(dTdt)

                elif node == (self.number_nodes - 1):
                    Ti = nodes_temp[node]
                    Ti_a = nodes_temp[node - 1]

                    dTdt = (c[node]['A'] * Ti +
                            c[node]['B'] * Ti_a +
                            c[node]['D'])

                    dzdt.append(dTdt)

                else:
                    Ti = nodes_temp[node]
                    Ti_b = nodes_temp[node + 1]
                    Ti_a = nodes_temp[node - 1]

                    dTdt = (c[node]['A'] * Ti +
                            c[node]['B'] * Ti_a +
                            c[node]['C'] * Ti_b +
                            c[node]['D'])

                    dzdt.append(dTdt)

            return dzdt

        # node indexes
        top = 0
        bottom = self.number_nodes - 1

        # CHANGED FROM
        # t = self.number_nodes - 1
        # CHANGED TO
        mass_flow_tot = self.mass_flow_calc(
            state, flow_temp, return_temp,
            source_temp, source_delta_t, thermal_output, demand,
            nodes_temp[bottom], nodes_temp[top]) * 3600
        # number of internal timesteps function of node mass and charging/dis mass
        t_ = math.ceil((mass_flow_tot / self.calc_node_mass()))
        # maximum internal timesteps is the number of nodes
        t = min(self.number_nodes, t_)
        # minimum internal timesteps is 1
        t = max(t, 1)

        # initial condition of coefficients
        coefficients = []
        # divide thermal output and demand accross timesteps
        # convert from kWh to kJ
        thermal_output = thermal_output * 3600 / float(t)
        demand = demand * 3600 / float(t)

        coefficients.append((self.set_of_coefficients(
            state, nodes_temp, source_temp, source_delta_t, flow_temp,
            return_temp, thermal_output, demand,
            nodes_temp[bottom], nodes_temp[top], timestep)))

        node_temp_list = []
        # node_temp_list.append(nodes_temp)

        # solve ODE
        for i in range(1, t + 1):
            # span for next time step
            tspan = [i - 1, i]
            # solve for next step
            # new coefficients
            coefficients.append((self.set_of_coefficients(
                state, nodes_temp, source_temp, source_delta_t,
                flow_temp, return_temp, thermal_output, demand,
                nodes_temp[bottom], nodes_temp[top], timestep)))

            z = odeint(
                model_temp, nodes_temp, tspan,
                args=(coefficients[i],))

            nodes_temp = z[1]
            nodes_temp = sorted(nodes_temp, reverse=True)
            node_temp_list.append(nodes_temp)
        return node_temp_list

    def coefficient_A_max(self, state, node, nodes_temp, source_temp,
                          flow_temp):

        node_mass = self.calc_node_mass()

        # specific heat at temperature of node i
        cp = self.specific_heat_water(nodes_temp[node])

        # thermal conductivity of insulation material
        k = self.insulation_k_value()

        # dimensions
        r1 = self.internal_radius()
        r2 = self.dimensions['width']
        h = self.dimensions['height']

        # correction factors
        Fi = self.correction_factors['insulation_factor']
        Fe = self.correction_factors['overall_factor']

        Fd = self.discharging_function(state, nodes_temp, flow_temp)[node]
        mf = self.mixing_function(state, node, nodes_temp,
                                  source_temp, flow_temp)

        Fco = self.charging_top_node(state)[node]

        mass_flow = self.calc_node_mass()

        A = (- Fd * mass_flow * cp -
             mf['Fdnt'] * mass_flow * cp -
             mf['Fcnb'] * mass_flow * cp -
             Fco * mass_flow * cp -
             Fe * Fi * k * ((1) / (r2 - r1)) *
             math.pi * ((r1 ** 2) + h * (r2 + r1))
             ) / (node_mass * cp)

        return A

    def coefficient_B_max(self, state, node, nodes_temp, source_temp,
                          flow_temp):

        node_mass = self.calc_node_mass()
        mf = self.mixing_function(state, node, nodes_temp,
                                  source_temp, flow_temp)
        mass_flow = self.calc_node_mass()

        B = mf['Fcnt'] * mass_flow / node_mass

        return B

    def coefficient_C_max(self, state, node, nodes_temp, source_temp,
                          flow_temp, timestep):

        node_mass = self.calc_node_mass()
        mf = self.mixing_function(state, node, nodes_temp,
                                  source_temp, flow_temp)
        mass_flow = node_mass

        C = mf['Fdnb'] * mass_flow / node_mass

        return C

    def coefficient_D_max(self, state, node, nodes_temp, source_temp,
                          flow_temp, return_temp, timestep):

        node_mass = self.calc_node_mass()

        # specific heat at temperature of node i
        cp = self.specific_heat_water(nodes_temp[node])

        # thermal conductivity of insulation material
        k = self.insulation_k_value()

        # dimensions
        r1 = self.internal_radius()
        r2 = self.dimensions['width']
        h = self.dimensions['height']

        # correction factors
        Fi = self.correction_factors['insulation_factor']
        Fe = self.correction_factors['overall_factor']

        Fc = self.charging_function(state, nodes_temp, source_temp)[node]
        Fdi = self.discharging_bottom_node(
            state, nodes_temp, return_temp, flow_temp)[node]
        Ta = self.amb_temp(timestep)

        cl = self.connection_losses()

        mass_flow = node_mass

        D = (Fc * mass_flow * cp * source_temp +
             Fdi * mass_flow * cp * return_temp +
             Fe * Fi * k * ((Ta) / (r2 - r1)) * math.pi *
             ((r1 ** 2) + h * (r2 + r1)) + Fe * cl
             ) / (node_mass * cp)

        return D

    def set_of_max_coefficients(self, state, nodes_temp, source_temp,
                                flow_temp, return_temp, timestep):

        c = []
        for node in range(self.number_nodes):
            coefficients = {'A': self.coefficient_A_max(
                state, node, nodes_temp, source_temp, flow_temp),
                            'B': self.coefficient_B_max(
                state, node, nodes_temp, source_temp, flow_temp),
                            'C': self.coefficient_C_max(
                state, node, nodes_temp, source_temp, flow_temp,
                timestep),
                            'D': self.coefficient_D_max(
                state, node, nodes_temp, source_temp, flow_temp,
                return_temp, timestep)}
            c.append(coefficients)
        return c

    def max_energy_in_out(self, state, nodes_temp, source_temp,
                          flow_temp, return_temp, timestep):

        # for node in range(len(nodes_temp)):
        #     if nodes_temp[node] > source_temp:
        #         nodes_temp[node] = source_temp

        nodes_temp_sum = 0.0
        for node in range(len(nodes_temp)):
            nodes_temp_sum += nodes_temp[node]
        if nodes_temp_sum >= source_temp * len(nodes_temp) and state == 'charging':
            return 0.0

        if nodes_temp_sum <= return_temp * len(nodes_temp) and state == 'discharging':
            return 0.0

        if self.capacity == 0:
            return 0.0

        def model_temp(z, t, c):
            dzdt = []
            for node in range(self.number_nodes):

                if node == 0:
                    Ti = nodes_temp[node]
                    Ti_b = nodes_temp[node + 1]

                    dTdt = (c[node]['A'] * Ti +
                            c[node]['C'] * Ti_b +
                            c[node]['D'])

                    dzdt.append(dTdt)

                elif node == (self.number_nodes - 1):
                    Ti = nodes_temp[node]
                    Ti_a = nodes_temp[node - 1]

                    dTdt = (c[node]['A'] * Ti +
                            c[node]['B'] * Ti_a +
                            c[node]['D'])

                    dzdt.append(dTdt)

                else:
                    Ti = nodes_temp[node]
                    Ti_b = nodes_temp[node + 1]
                    Ti_a = nodes_temp[node - 1]

                    dTdt = (c[node]['A'] * Ti +
                            c[node]['B'] * Ti_a +
                            c[node]['C'] * Ti_b +
                            c[node]['D'])

                    dzdt.append(dTdt)

            return dzdt

        # number of time points
        t = self.number_nodes - 1

        # initial condition of coefficients
        coefficients = []
        coefficients.append((self.set_of_max_coefficients(
            state, nodes_temp, source_temp,
            flow_temp, return_temp, timestep)))

        energy_list = []
        mass_flow = self.calc_node_mass()
        cp = self.specific_heat_water(source_temp)

        # solve ODE
        for i in range(1, t + 1):
            if state == 'charging' and source_temp > nodes_temp[self.number_nodes - 1]:
                energy = mass_flow * cp * (
                    source_temp - nodes_temp[self.number_nodes - 1])
            elif state == 'discharging' and nodes_temp[0] > flow_temp:
                energy = mass_flow * cp * (
                    nodes_temp[0] - return_temp)
            else:
                energy = 0
            energy_list.append(energy)
            # span for next time step
            tspan = [i - 1, i]
            # solve for next step
            # new coefficients
            coefficients.append((self.set_of_max_coefficients(
                state, nodes_temp, source_temp,
                flow_temp, return_temp, timestep)))

            z = odeint(
                model_temp, nodes_temp, tspan,
                args=(coefficients[i],))
            nodes_temp = z[1]

        # convert J to kWh by divide by 3600000
        energy_total = sum(energy_list) / 3600000
        return energy_total
