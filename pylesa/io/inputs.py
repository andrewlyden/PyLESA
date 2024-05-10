"""inputs modules

reads input pickle files for use in other modules
"""
import logging
import os
import pandas as pd

LOG = logging.getLogger(__name__)

class Inputs(object):

    def __init__(self, name, subname):

        self.folder_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "inputs", name[:-5], subname + '.pkl')
        self.container = pd.read_pickle(self.folder_path)

    def controller(self):

        controller_info = self.container['controller_info']
        horizon = self.container['horizon']
        import_setpoint = self.container['import_setpoint']
        fixed_order_info = self.container['fixed_order_info']

        inputs = {'controller_info': controller_info,
                  'horizon': horizon,
                  'import_setpoint': import_setpoint,
                  'fixed_order_info': fixed_order_info}

        return inputs

    def PV_model(self):
        """input data for PV class from the Excel sheet

        takes pickles created from main Excel input sheet
        and creates a dict with attributes for PV class

        Returns:
            dict -- inputs for the PV class
        """
        PV_spec = self.container['PV_spec']
        PV_location = self.container['PV_location']

        loc = PV_location.to_dict('list')
        spec = PV_spec.to_dict('list')

        inputs = {'module_name': spec['module'][0],
                  'inverter_name': spec['inverter'][0],
                  'multiplier': spec['multiplier'][0],
                  'surface_tilt': spec['surface_tilt'][0],
                  'surface_azimuth': spec['surface_azimuth'][0],
                  'surface_type': spec['surface_type'][0],
                  'loc_name': loc['name'][0],
                  'latitude': loc['latitude'][0],
                  'longitude': loc['longitude'][0],
                  'altitude': loc['altitude'][0]
                  }

        return inputs

    def windturbine_user(self):

        wind_user = self.container['wind_user']
        power_curve = self.container['power_curve']

        # create two dicts for holding csv data
        myTurbine = wind_user.to_dict('list')
        power_curve['value'] = [float(i) for i in power_curve['value']]
        power_curve['wind_speed'] = [float(i) for i in power_curve['wind_speed']]

        inputs = {'turbine_name': myTurbine['turbine_name'][0],
                  'hub_height': myTurbine['hub_height'][0],
                  'rotor_diameter': myTurbine['rotor_diameter'][0],
                  'multiplier': myTurbine['multiplier'][0],
                  'nominal_power': myTurbine['nominal_power'][0],
                  'power_curve': power_curve
                  }

        return inputs

    def windturbine_database(self):

        wind_database = self.container['wind_database']

        # create dict for holding csv data
        myTurbine = wind_database.to_dict('list')

        inputs = {'turbine_name': myTurbine['turbine_name'][0],
                  'hub_height': myTurbine['hub_height'][0],
                  'rotor_diameter': myTurbine['rotor_diameter'][0],
                  'multiplier': myTurbine['multiplier'][0]
                  }

        return inputs

    def wind_farm(self):

        return self.container['wind_farm']

    def wind_farm_weather(self):

        resources = self.container['wind_farm_resources']

        inputs = {'wind_speed_10': resources[['wind_speed_10']],
                  'wind_speed_50': resources[['wind_speed_50']],
                  'roughness_length': resources[['roughness_length']],
                  'pressure': resources[['pressure']],
                  'air_temperature': resources[['air_temperature']]
                  }

        return inputs

    def weather(self):

        resources = self.container['resources']

        inputs = {'DHI': resources[['DHI']],
                  'GHI': resources[['GHI']],
                  'DNI': resources[['DNI']],
                  'wind_speed_10': resources[['wind_speed_10']],
                  'wind_speed_50': resources[['wind_speed_50']],
                  'roughness_length': resources[['roughness_length']],
                  'pressure': resources[['pressure']],
                  'air_temperature': resources[['air_temperature']],
                  'air_density': resources[['air_density']],
                  'water_temperature': resources[['water_temperature']]
                  }

        return inputs

    def aux(self):

        spec = self.container['aux_heat']
        fuel_info = self.container['fuel_info']

        inputs = {'fuel': spec['fuel'],
                  'efficiency': spec['efficiency'],
                  'fuel_info': fuel_info}

        return inputs

    def demands(self):

        dem_var = self.container['demand_input_variable']
        dem_static = self.container['demand_input_static']

        inputs = {'heat_demand': dem_var['heat demand'],
                  'elec_demand': dem_var['electrical demand'],
                  'flow_temp_DH': dem_var['temp_flow'],
                  'return_temp_DH': dem_static['temp_return'],
                  'source_temp': dem_var['temp_source'],
                  'source_delta_t': dem_static['source_delta_t']}

        return inputs

    def RHI(self):

        RHI = self.container['RHI']

        RHI_type = RHI['RHI_type']
        tariff_type = RHI['tariff_type']
        fixed_rate = RHI['fixed_rate']
        tier_1 = RHI['tier_1']
        tier_2 = RHI['tier_2']

        inputs = {'RHI_type': RHI_type,
                  'tariff_type': tariff_type,
                  'fixed_rate': fixed_rate,
                  'tier_1': tier_1,
                  'tier_2': tier_2}

        return inputs

    def heatpump_basics(self):

        hp = self.container['hp_basics']

        # the inputs which specify the heat pump to be modelled
        hp_type = hp['heat_pump_type'][0]
        capacity = hp['capacity'][0]
        modelling_approach = hp['modelling_approach'][0]
        ambient_delta_t = hp['ambient_delta_t'][0]
        minimum_runtime = hp['minimum_runtime'][0]
        data_input = hp['data_input'][0]
        minimum_output = hp['minimum_output'][0]

        inputs = {'heat_pump_type': hp_type,
                  'capacity': capacity,
                  'modelling_approach': modelling_approach,
                  'ambient_delta_t': ambient_delta_t,
                  'minimum_runtime': minimum_runtime,
                  'data_input': data_input,
                  'minimum_output': minimum_output}

        return inputs

    def heatpump_simple(self):

        hp = self.container['hp_simple']
        cop = hp

        return cop

    def heatpump_lorentz(self):

        lorentz = self.container['lorentz']

        cop = lorentz['COP'][0]
        flow_temp_spec = lorentz['flow_temp'][0]
        return_temp_spec = lorentz['return_temp'][0]
        temp_ambient_in_spec = lorentz['ambient_temp_in'][0]
        temp_ambient_out_spec = lorentz['ambient_temp_out'][0]
        elec_capacity = lorentz['elec_capacity'][0]

        inputs = {'cop': cop,
                  'flow_temp_spec': flow_temp_spec,
                  'return_temp_spec': return_temp_spec,
                  'temp_ambient_in_spec': temp_ambient_in_spec,
                  'temp_ambient_out_spec': temp_ambient_out_spec,
                  'elec_capacity': elec_capacity}

        return inputs

    def heatpump_standard_regression(self):

        regression1 = self.container['regression1']
        regression_temp1 = self.container['regression_temp1']

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

        regression2 = self.container['regression2']
        regression_temp2 = self.container['regression_temp2']

        dic2 = {'flow_temp': [regression_temp2['flow_temp'][0],
                              regression_temp2['flow_temp'][0],
                              regression_temp2['flow_temp'][0],
                              regression_temp2['flow_temp'][0],
                              regression_temp2['flow_temp'][0],
                              regression_temp2['flow_temp'][0],
                              regression_temp2['flow_temp'][0],
                              regression_temp2['flow_temp'][0]]}

        df2 = pd.DataFrame(data=dic2)
        data2 = pd.concat([regression2, df2], axis=1)

        regression3 = self.container['regression3']
        regression_temp3 = self.container['regression_temp3']

        dic3 = {'flow_temp': [regression_temp3['flow_temp'][0],
                              regression_temp3['flow_temp'][0],
                              regression_temp3['flow_temp'][0],
                              regression_temp3['flow_temp'][0],
                              regression_temp3['flow_temp'][0],
                              regression_temp3['flow_temp'][0],
                              regression_temp3['flow_temp'][0],
                              regression_temp3['flow_temp'][0]]}

        df3 = pd.DataFrame(data=dic3)
        data3 = pd.concat([regression3, df3], axis=1)

        regression4 = self.container['regression4']
        regression_temp4 = self.container['regression_temp4']

        dic4 = {'flow_temp': [regression_temp4['flow_temp'][0],
                              regression_temp4['flow_temp'][0],
                              regression_temp4['flow_temp'][0],
                              regression_temp4['flow_temp'][0],
                              regression_temp4['flow_temp'][0],
                              regression_temp4['flow_temp'][0],
                              regression_temp4['flow_temp'][0],
                              regression_temp4['flow_temp'][0]]}

        df4 = pd.DataFrame(data=dic4)
        data4 = pd.concat([regression4, df4], axis=1)

        regression_data = pd.concat([data1, data2, data3, data4], ignore_index=True)
        regression_data = regression_data.dropna()
        regression_data = regression_data.reset_index(drop=True)

        # note that ambient temp is column1 and flow is column 2
        X = regression_data.drop(
            columns=['duty', 'capacity_percentage', 'COSP'])

        Y_COSP = regression_data.drop(
            columns=['duty', 'capacity_percentage', 'flow_temp', 'ambient_temp'])
        Y_duty = regression_data.drop(
            columns=['COSP', 'capacity_percentage', 'flow_temp', 'ambient_temp'])

        inputs = {'data_x': X,
                  'data_COSP': Y_COSP,
                  'data_duty': Y_duty}

        return inputs

    def hot_water_tank(self):

        ts = self.container['thermal_storage']

        capacity = ts['capacity'][0]
        insulation = ts['insulation'][0]
        location = ts['location'][0]
        number_nodes = ts['number_nodes'][0]

        dimensions = {'height': ts['height'][0],
                      'width': ts['width'][0],
                      'insulation_thickness': ts['insulation_thickness'][0]
                      }

        tank_openings = {'tank_opening': ts['tank_opening'][0],
                         'tank_opening_diameter': ts['tank_opening_diameter'][0],
                         'uninsulated_connections': ts['uninsulated_connections'][0],
                         'uninsulated_connections_diameter': ts['uninsulated_connections_diameter'][0],
                         'insulated_connections': ts['insulated_connections'][0],
                         'insulated_connections_diameter': ts['insulated_connections_diameter'][0]
                         }

        correction_factors = {'insulation_factor': ts['insulation_factor'][0],
                              'overall_factor': ts['overall_factor'][0]}

        inputs = {'capacity': capacity,
                  'insulation': insulation,
                  'location': location,
                  'number_nodes': number_nodes,
                  'dimensions': dimensions,
                  'tank_openings': tank_openings,
                  'correction_factors': correction_factors}

        return inputs

    def grid(self):

        export = self.container['export']
        tariff_choice = self.container['tariff_choice']
        balancing_mechanism = self.container['balancing_mechanism']
        grid_services = self.container['grid_services']
        grid_services_series = self.container['grid_services_series']
        flat_rates = self.container['flat_rates']
        variable_periods = self.container['variable_periods']
        variable_periods_year = self.container['variable_periods_year']
        wholesale_market = self.container['wholesale_market']
        balancing_mechanism_series = self.container['balancing_mechanism_series']
        ppa_output = self.container['ppa_output']
        wm_info = self.container['wm_info']
        ppa_info = self.container['ppa_info']

        inputs = {'tariff_choice': tariff_choice,
                  'balancing_mechanism': balancing_mechanism,
                  'grid_services': grid_services,
                  'grid_services_series': grid_services_series,
                  'flat_rates': flat_rates,
                  'variable_periods': variable_periods,
                  'variable_periods_year': variable_periods_year,
                  'wholesale_market': wholesale_market,
                  'balancing_mechanism_series': balancing_mechanism_series,
                  'ppa_output': ppa_output,
                  'wm_info': wm_info,
                  'ppa_info': ppa_info,
                  'export': export}

        return inputs

    def electrical_storage(self):

        es = self.container['electrical_storage']

        capacity = es['capacity'][0]
        initial_state = es['initial state'][0]
        charge_max = es['charge max'][0]
        discharge_max = es['discharge max'][0]
        charge_eff = es['charge eff'][0]
        discharge_eff = es['discharge eff'][0]
        self_discharge = es['self discharge'][0]

        inputs = {'capacity': capacity,
                  'initial_state': initial_state,
                  'charge_max': charge_max,
                  'discharge_max': discharge_max,
                  'charge_eff': charge_eff,
                  'discharge_eff': discharge_eff,
                  'self_discharge': self_discharge}

        return inputs
