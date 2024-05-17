"""reads the excel input sheet

reads and then writes input pickle files
"""
import logging
from pathlib import Path
import pickle
import shutil
import pandas as pd

from .paths import valid_fpath
from ..constants import INDIR, OUTDIR

LOG = logging.getLogger(__name__)

def read_inputs(xlsxpath: str | Path, root: Path) -> None:
    """Read all inputs from MS Excel workbook and setup directories
    
    Args:
        xlsxpath: path to MS Excel workbook containing inputs
        root: path to directory to store intermediary inputs and outputs
    """
    xlsxpath = valid_fpath(xlsxpath)
    LOG.info(f'Reading MS Excel file: {xlsxpath.name}')
    root = Path(root).resolve()
    myInput = XlsxInput(xlsxpath, root)

    myInput.parametric_analysis()
    myInput.controller()
    myInput.resources()
    myInput.demands()
    myInput.demand_input()
    myInput.PV()
    myInput.wind()
    myInput.wind_farm()
    myInput.electrical_storage()
    myInput.grid()
    myInput.aux()
    myInput.thermal_storage()
    myInput.heat_pump()

    # write to pickle file
    file = root / INDIR / 'inputs.pkl'
    with open(file, 'wb') as handle:
        pickle.dump(myInput.container, handle, protocol=pickle.HIGHEST_PROTOCOL)

    LOG.info(f'Completed reading MS Excel file: {xlsxpath.name}')


class XlsxInput(object):

    def __init__(self, xlsxpath: Path, root: Path):

        # name of excel sheet
        self.xlsxpath = Path(xlsxpath).resolve()
        self.root = Path(root).resolve()

        # data containter
        self.container = {}

        # path to folder for inputs
        self.folder_path = self.root / INDIR
        if self.folder_path.is_dir() is False:
            self.folder_path.mkdir()
        elif self.folder_path.is_dir() is True:
            shutil.rmtree(self.folder_path)
            self.folder_path.mkdir()

        # read excel sheet
        self.excel_sheets = pd.read_excel(xlsxpath, sheet_name=None)

        # create outputs folder
        out_path = self.root / OUTDIR
        if out_path.is_dir() is False:
            out_path.mkdir()
        elif out_path.is_dir() is True:
            shutil.rmtree(out_path)
            out_path.mkdir()

    def parametric_analysis(self):

        df = self.excel_sheets['Parametric']
        hp_max = df['Unnamed: 3'][4]
        hp_min = df['Unnamed: 4'][4]
        hp_step = df['Unnamed: 5'][4]
        ts_max = df['Unnamed: 3'][5]
        ts_min = df['Unnamed: 4'][5]
        ts_step = df['Unnamed: 5'][5]

        data = {'hp_max': hp_max,
                'hp_min': hp_min,
                'hp_step': hp_step,
                'ts_max': ts_max,
                'ts_min': ts_min,
                'ts_step': ts_step}

        self.container['parametric_analysis'] = data

    def controller(self):

        df = self.excel_sheets['Controller']

        controller = df['Unnamed: 3'][3]
        first_hour = df['Unnamed: 6'][3]
        total_timesteps = df['Unnamed: 6'][4]
        controller_info = {'controller': controller,
                           'first_hour': first_hour,
                           'total_timesteps': total_timesteps}

        self.container['controller_info'] = controller_info

        import_setpoint = df['Unnamed: 3'][5]
        self.container['import_setpoint'] = import_setpoint

        horizon = df['Unnamed: 6'][7]
        self.container['horizon'] = horizon

        order_below_setpoint = df['Unnamed: 3'][7]
        ls = order_below_setpoint.split(',')
        order_below_setpoint = [int(i) for i in ls]
        order_above_setpoint = df['Unnamed: 3'][6]
        ls = order_above_setpoint.split(',')
        order_above_setpoint = [int(i) for i in ls]
        fixed_order_info = {'order_below_setpoint': order_below_setpoint,
                            'order_above_setpoint': order_above_setpoint}
        self.container['fixed_order_info'] = fixed_order_info

    def resources(self):

        df = self.excel_sheets['Weather resources']
        df = df.drop(columns=['Unnamed: 0', 'Unnamed: 1', 'Unnamed: 2',
                              'Unnamed: 13', 'Unnamed: 14'],
                     index=[0, 1, 2, 3])
        df = df.rename(columns={'Unnamed: 3': 'DHI',
                                'Unnamed: 4': 'GHI',
                                'Unnamed: 5': 'DNI',
                                'Unnamed: 6': 'wind_speed_10',
                                'Unnamed: 7': 'wind_speed_50',
                                'Unnamed: 8': 'roughness_length',
                                'Unnamed: 9': 'pressure',
                                'Unnamed: 10': 'air_temperature',
                                'Unnamed: 11': 'air_density',
                                'Unnamed: 12': 'water_temperature'})
        df = df.reset_index(drop=True)

        self.container['resources'] = df

    def demands(self):

        df = self.excel_sheets['Demand gen']

        hot_water = df['Unnamed: 3'][15]
        self.container['hot_water'] = hot_water

        dem = df.drop(index=[0, 1, 2, 3],
                      columns=['Unnamed: 0', 'Unnamed: 1',
                               'Unnamed: 2', 'Unnamed: 7'])
        list1 = []
        for x in range(14, 36):
            list1.append(x)
        dem = dem.drop(list1)
        dem = dem.rename(columns={'Unnamed: 3': 'Type',
                                  'Unnamed: 4': 'Age',
                                  'Unnamed: 5': 'Bedrooms',
                                  'Unnamed: 6': 'Number of type'})
        dem = dem.reset_index(drop=True)
        self.container['heating'] = dem

    def demand_input(self):
        df = self.excel_sheets['Demand input']

        temp_return = df['Unnamed: 8'][4]
        source_delta_t = df['Unnamed: 8'][6]
        data = {'temp_return': temp_return,
                'source_delta_t': source_delta_t}

        self.container['demand_input_static'] = data

        df = df.drop(columns=['Unnamed: 0', 'Unnamed: 1', 'Unnamed: 2',
                              'Unnamed: 7', 'Unnamed: 8'],
                     index=[0, 1, 2, 3])
        df = df.rename(columns={'Unnamed: 3': 'heat demand',
                                'Unnamed: 4': 'electrical demand',
                                'Unnamed: 5': 'temp_flow',
                                'Unnamed: 6': 'temp_source'})
        df = df.reset_index(drop=True)

        self.container['demand_input_variable'] = df

    def PV(self):

        df = self.excel_sheets['PV inputs']

        PV_location = df.drop(columns=['Unnamed: 0', 'Unnamed: 1',
                                       'Unnamed: 6', 'Unnamed: 7'],
                              index=[13, 17, 18])
        PV_location = PV_location.dropna(axis='index', how='any')
        PV_location = PV_location.rename(columns={'Unnamed: 2': 'name',
                                                  'Unnamed: 3': 'latitude',
                                                  'Unnamed: 4': 'longitude',
                                                  'Unnamed: 5': 'altitude'})
        PV_location = PV_location.reset_index(drop=True)
        self.container['PV_location'] = PV_location

        PV_spec = df.drop(columns=['Unnamed: 0', 'Unnamed: 1'],
                          index=[17])
        PV_spec = PV_spec.dropna(axis='index', how='any')
        PV_spec = PV_spec.rename(columns={'Unnamed: 2': 'module',
                                          'Unnamed: 3': 'inverter',
                                          'Unnamed: 4': 'multiplier',
                                          'Unnamed: 5': 'surface_tilt',
                                          'Unnamed: 6': 'surface_azimuth',
                                          'Unnamed: 7': 'surface_type'})
        PV_spec = PV_spec.reset_index(drop=True)
        self.container['PV_spec'] = PV_spec

    def wind(self):

        df = self.excel_sheets['Wind inputs']

        wind_database = df.drop(columns=['Unnamed: 0', 'Unnamed: 1',
                                         'Unnamed: 6'],
                                index=[12, 17, 18])
        wind_database = wind_database.dropna(axis='index', how='any')
        wind_database = wind_database.rename(
            columns={'Unnamed: 2': 'turbine_name',
                     'Unnamed: 3': 'hub_height',
                     'Unnamed: 4': 'rotor_diameter',
                     'Unnamed: 5': 'multiplier'})
        wind_database = wind_database.reset_index(drop=True)
        self.container['wind_database'] = wind_database

        my_turbine = df.drop(columns=['Unnamed: 0', 'Unnamed: 1'],
                             index=[17])
        my_turbine = my_turbine.dropna(axis='index', how='any')
        my_turbine = my_turbine.rename(
            columns={'Unnamed: 2': 'turbine_name',
                     'Unnamed: 3': 'hub_height',
                     'Unnamed: 4': 'rotor_diameter',
                     'Unnamed: 5': 'multiplier',
                     'Unnamed: 6': 'nominal_power'})
        my_turbine = my_turbine.reset_index(drop=True)
        self.container['wind_user'] = my_turbine

        power_curve = df.drop(columns=['Unnamed: 0', 'Unnamed: 1',
                                       'Unnamed: 4', 'Unnamed: 5',
                                       'Unnamed: 6'],
                              index=[12, 13, 17, 18, 21])
        power_curve = power_curve.dropna(axis='index', how='any')
        power_curve = power_curve.rename(
            columns={'Unnamed: 2': 'value',
                     'Unnamed: 3': 'wind_speed'})
        power_curve = power_curve.reset_index(drop=True)
        self.container['power_curve'] = power_curve

    def wind_farm(self):
        df = self.excel_sheets['Wind farm']

        turbine_name = df['Unnamed: 2'][13]
        hub_height = df['Unnamed: 3'][13]
        rotor_diameter = df['Unnamed: 4'][13]
        number_of_turbines = df['Unnamed: 5'][13]
        efficiency = df['Unnamed: 6'][13]

        wind_farm = {'turbine_name': turbine_name,
                     'hub_height': hub_height,
                     'rotor_diameter': rotor_diameter,
                     'number_of_turbines': number_of_turbines,
                     'efficiency': efficiency}
        self.container['wind_farm'] = wind_farm

        df = df.drop(columns=['Unnamed: 0', 'Unnamed: 1'],
                     index=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                            11, 12, 13, 14, 15, 16, 17])
        df = df.rename(columns={'Unnamed: 2': 'wind_speed_10',
                                'Unnamed: 3': 'wind_speed_50',
                                'Unnamed: 4': 'roughness_length',
                                'Unnamed: 5': 'pressure',
                                'Unnamed: 6': 'air_temperature'})
        df = df.reset_index(drop=True)
        self.container['wind_farm_resources'] = df

    def electrical_storage(self):
        df = self.excel_sheets['Electrical storage']

        df = df.drop(columns=['Unnamed: 0', 'Unnamed: 1'],
                     index=[3])
        df = df.dropna(axis='index', how='any')
        df = df.rename(
            columns={'Unnamed: 2': 'capacity',
                     'Unnamed: 3': 'initial state',
                     'Unnamed: 4': 'charge max',
                     'Unnamed: 5': 'discharge max',
                     'Unnamed: 6': 'charge eff',
                     'Unnamed: 7': 'discharge eff',
                     'Unnamed: 8': 'self discharge'})
        df = df.reset_index(drop=True)
        self.container['electrical_storage'] = df

    def grid(self):
        df = self.excel_sheets['Grid']

        export = df['Unnamed: 3'][7]
        self.container['export'] = export

        tariff_choice = df['Unnamed: 3'][3]
        self.container['tariff_choice'] = tariff_choice

        balancing_mechanism = df['Unnamed: 7'][3]
        self.container['balancing_mechanism'] = balancing_mechanism

        grid_services = df['Unnamed: 9'][3]
        self.container['grid_services'] = grid_services

        df = df.drop(columns=['Unnamed: 0', 'Unnamed: 1',
                              'Unnamed: 14', 'Unnamed: 15', 'Unnamed: 16',
                              'Unnamed: 17', 'Unnamed: 18', 'Unnamed: 19',
                              'Unnamed: 20', 'Unnamed: 21', 'Unnamed: 22'])

        grid_services_series = df.drop(
            columns=['Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4', 'Unnamed: 6',
                     'Unnamed: 5', 'Unnamed: 10', 'Unnamed: 11',
                     'Unnamed: 12', 'Unnamed: 13'],
            index=[3, 5])
        grid_services_series = grid_services_series.drop(
            index=[9, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
                   26, 17, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39])
        grid_services_series = grid_services_series.dropna(
            axis='index', how='any')
        grid_services_series = grid_services_series.rename(
            columns={'Unnamed: 7': 'STOR',
                     'Unnamed: 8': 'FFR',
                     'Unnamed: 9': 'capacity_market'},
            index={10: 'notice_period',
                   11: 'payment',
                   12: 'frequency'})
        self.container['grid_services_series'] = grid_services_series

        flat_rate_import = df['Unnamed: 2'][7]
        flat_rate_export = df['Unnamed: 3'][7]
        flat_rates = {'import': flat_rate_import, 'export': flat_rate_export}
        self.container['flat_rates'] = flat_rates

        variable_periods = df.iloc[16:40]
        variable_periods = variable_periods.drop(
            columns=['Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4',
                     'Unnamed: 5', 'Unnamed: 6'])
        variable_periods = variable_periods.rename(
            columns={'Unnamed: 7': 'Monday',
                     'Unnamed: 8': 'Tuesday',
                     'Unnamed: 9': 'Wednesday',
                     'Unnamed: 10': 'Thursday',
                     'Unnamed: 11': 'Friday',
                     'Unnamed: 12': 'Saturday',
                     'Unnamed: 13': 'Sunday'})
        variable_periods = variable_periods.reset_index(drop=True)
        self.container['variable_periods'] = variable_periods

        variable_periods_year = df['Unnamed: 13'][40]
        self.container['variable_periods_year'] = variable_periods_year

        wholesale_market = df.iloc[10:8770]
        wholesale_market = wholesale_market.drop(
            columns=['Unnamed: 3', 'Unnamed: 4', 'Unnamed: 5',
                     'Unnamed: 7', 'Unnamed: 8', 'Unnamed: 6',
                     'Unnamed: 9', 'Unnamed: 10',
                     'Unnamed: 11', 'Unnamed: 12',
                     'Unnamed: 13'])
        wholesale_market = wholesale_market.rename(columns={
            'Unnamed: 2': 'wholesale_market'})
        wholesale_market = wholesale_market.reset_index(drop=True)
        self.container['wholesale_market'] = wholesale_market

        balancing_mechanism_series = df.iloc[10:8770]
        balancing_mechanism_series = balancing_mechanism_series.drop(
            columns=['Unnamed: 2', 'Unnamed: 4', 'Unnamed: 5',
                     'Unnamed: 7', 'Unnamed: 8', 'Unnamed: 6',
                     'Unnamed: 9', 'Unnamed: 10',
                     'Unnamed: 11', 'Unnamed: 12',
                     'Unnamed: 13'])
        balancing_mechanism_series = balancing_mechanism_series.rename(
            columns={'Unnamed: 3': 'balancing_mechanism'})
        balancing_mechanism_series = balancing_mechanism_series.reset_index(
            drop=True)
        self.container['balancing_mechanism_series'] = balancing_mechanism_series

        ppa_output = df.iloc[10:8770]
        ppa_output = ppa_output.drop(
            columns=['Unnamed: 2', 'Unnamed: 3', 'Unnamed: 5',
                     'Unnamed: 7', 'Unnamed: 8', 'Unnamed: 6',
                     'Unnamed: 9', 'Unnamed: 10',
                     'Unnamed: 11', 'Unnamed: 12',
                     'Unnamed: 13'])
        ppa_output = ppa_output.rename(columns={
            'Unnamed: 4': 'ppa_output'})
        ppa_output = ppa_output.reset_index(drop=True)
        self.container['ppa_output'] = ppa_output

        premium = df['Unnamed: 6'][7]
        maximum = df['Unnamed: 7'][7]

        lower_percent = df['Unnamed: 9'][7]
        higher_percent = df['Unnamed: 10'][7]
        lower_penalty = df['Unnamed: 11'][7]
        higher_discount = df['Unnamed: 12'][7]

        wm_info = {'premium': premium,
                   'maximum': maximum}
        self.container['wm_info'] = wm_info

        ppa_info = {'lower_percent': lower_percent,
                    'higher_percent': higher_percent,
                    'lower_penalty': lower_penalty,
                    'higher_discount': higher_discount}
        self.container['ppa_info'] = ppa_info

    def aux(self):

        df = self.excel_sheets['Aux heat']

        fuel = df['Unnamed: 2'][4]
        efficiency = df['Unnamed: 3'][4]
        data = {'fuel': fuel, 'efficiency': efficiency}
        self.container['aux_heat'] = data

        # fuel then energy density and cost
        fuel_info = {
            df['Unnamed: 2'][7]: {
                'energy_density': df['Unnamed: 3'][7],
                'cost': df['Unnamed: 4'][7]},
            df['Unnamed: 2'][8]: {
                'energy_density': df['Unnamed: 3'][8],
                'cost': df['Unnamed: 4'][8]},
            df['Unnamed: 2'][9]: {
                'energy_density': df['Unnamed: 3'][9],
                'cost': df['Unnamed: 4'][9]}}
        self.container['fuel_info'] = fuel_info

    def thermal_storage(self):

        df = self.excel_sheets['Thermal storage']

        df = df.transpose()
        df = df.reset_index(drop=True)
        df = df.drop(index=[0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                     columns=[0, 1, 2, 7, 11, 18, 19])
        df = df.rename(columns={3: 'capacity', 4: 'insulation',
                                5: 'location', 6: 'number_nodes',
                                8: 'height', 9: 'width',
                                10: 'insulation_thickness',
                                12: 'tank_opening',
                                13: 'tank_opening_diameter',
                                14: 'uninsulated_connections',
                                15: 'uninsulated_connections_diameter',
                                16: 'insulated_connections',
                                17: 'insulated_connections_diameter',
                                20: 'insulation_factor',
                                21: 'overall_factor'
                                })
        df = df.reset_index(drop=True)
        self.container['thermal_storage'] = df

    def heat_pump(self):

        df = self.excel_sheets['Heat pump']

        hp_basics = df.iloc[1:8]
        hp_basics = hp_basics.transpose()
        hp_basics = hp_basics.reset_index(drop=True)
        hp_basics = hp_basics.drop(
            [0, 1, 2, 4, 5, 6, 7, 8, 9, 10])
        hp_basics = hp_basics.rename(columns={1: 'heat_pump_type',
                                              2: 'modelling_approach',
                                              3: 'capacity',
                                              4: 'ambient_delta_t',
                                              5: 'minimum_runtime',
                                              6: 'minimum_output',
                                              7: 'data_input'})
        hp_basics = hp_basics.reset_index(drop=True)
        self.container['hp_basics'] = hp_basics

        # RHI inputs
        RHI_type = df['Unnamed: 13'][3]
        tariff_type = df['Unnamed: 13'][4]
        fixed_rate = df['Unnamed: 13'][5]
        tier_1 = df['Unnamed: 13'][6]
        tier_2 = df['Unnamed: 13'][7]

        RHI = {'RHI_type': RHI_type,
               'tariff_type': tariff_type,
               'fixed_rate': fixed_rate,
               'tier_1': tier_1,
               'tier_2': tier_2}
        self.container['RHI'] = RHI

        simple = df.iloc[9:11]
        simple = simple['Unnamed: 3'][10]
        self.container['hp_simple'] = simple

        lorentz = df.iloc[13:19]
        lorentz = lorentz.transpose()
        lorentz = lorentz.reset_index(drop=True)
        lorentz = lorentz.drop(
            [0, 1, 2, 4, 5, 6, 7, 8, 9, 10,
             11, 12, 13, 14, 15, 16, 17, 18])
        lorentz = lorentz.rename(columns={13: 'COP',
                                          14: 'flow_temp',
                                          15: 'return_temp',
                                          16: 'ambient_temp_in',
                                          17: 'ambient_temp_out',
                                          18: 'elec_capacity'})
        lorentz = lorentz.reset_index(drop=True)
        self.container['lorentz'] = lorentz

        regression_temp1 = df.iloc[21:25]
        regression_temp1 = regression_temp1.transpose()
        regression_temp1 = regression_temp1.reset_index(drop=True)
        regression_temp1 = regression_temp1.drop(
            [0, 1, 2, 4, 5, 6, 7, 8, 9, 10,
             11, 12, 13, 14, 15, 16, 17, 18])
        regression_temp1 = regression_temp1.drop(columns=[23, 24])
        regression_temp1 = regression_temp1.rename(columns={21: 'flow_temp',
                                                            22: 'return_temp'})
        regression_temp1 = regression_temp1.reset_index(drop=True)
        self.container['regression_temp1'] = regression_temp1

        regression_temp2 = df.iloc[21:25]
        regression_temp2 = regression_temp2.transpose()
        regression_temp2 = regression_temp2.reset_index(drop=True)
        regression_temp2 = regression_temp2.drop(
            [0, 1, 2, 3, 4, 5, 6, 8, 9, 10,
             11, 12, 13, 14, 15, 16, 17, 18])
        regression_temp2 = regression_temp2.drop(columns=[23, 24])
        regression_temp2 = regression_temp2.rename(columns={21: 'flow_temp',
                                                            22: 'return_temp'})
        regression_temp2 = regression_temp2.reset_index(drop=True)
        self.container['regression_temp2'] = regression_temp2

        regression_temp3 = df.iloc[34:36]
        regression_temp3 = regression_temp3.transpose()
        regression_temp3 = regression_temp3.reset_index(drop=True)
        regression_temp3 = regression_temp3.drop(
            [0, 1, 2, 4, 5, 6, 7, 8, 9, 10,
             11, 12, 13, 14, 15, 16, 17, 18])
        regression_temp3 = regression_temp3.rename(columns={34: 'flow_temp',
                                                            35: 'return_temp'})
        regression_temp3 = regression_temp3.reset_index(drop=True)
        self.container['regression_temp3'] = regression_temp3

        regression_temp4 = df.iloc[34:36]
        regression_temp4 = regression_temp4.transpose()
        regression_temp4 = regression_temp4.reset_index(drop=True)
        regression_temp4 = regression_temp4.drop(
            [0, 1, 2, 3, 4, 5, 6, 8, 9, 10,
             11, 12, 13, 14, 15, 16, 17, 18])
        regression_temp4 = regression_temp4.rename(columns={34: 'flow_temp',
                                                            35: 'return_temp'})
        regression_temp4 = regression_temp4.reset_index(drop=True)
        self.container['regression_temp4'] = regression_temp4

        regression1 = df.iloc[23:33]
        regression1 = regression1.drop(columns={'Unnamed: 0', 'Unnamed: 1',
                                                'Unnamed: 6', 'Unnamed: 7',
                                                'Unnamed: 8', 'Unnamed: 9',
                                                'Unnamed: 10', 'Unnamed: 11',
                                                'Unnamed: 12', 'Unnamed: 13',
                                                'Unnamed: 14', 'Unnamed: 15',
                                                'Unnamed: 16', 'Unnamed: 17',
                                                'Unnamed: 18'})
        regression1 = regression1.rename(columns={'Unnamed: 2': 'ambient_temp',
                                                  'Unnamed: 3': 'COSP',
                                                  'Unnamed: 4': 'duty',
                                                  'Unnamed: 5': 'capacity_percentage'})
        regression1 = regression1.drop([23, 24])
        regression1 = regression1.reset_index(drop=True)
        self.container['regression1'] = regression1

        regression2 = df.iloc[23:33]
        regression2 = regression2.drop(columns={'Unnamed: 0', 'Unnamed: 1',
                                                'Unnamed: 2', 'Unnamed: 3',
                                                'Unnamed: 4', 'Unnamed: 5',
                                                'Unnamed: 10', 'Unnamed: 11',
                                                'Unnamed: 12', 'Unnamed: 13',
                                                'Unnamed: 14', 'Unnamed: 15',
                                                'Unnamed: 16', 'Unnamed: 17',
                                                'Unnamed: 18'})
        regression2 = regression2.rename(columns={'Unnamed: 6': 'ambient_temp',
                                                  'Unnamed: 7': 'COSP',
                                                  'Unnamed: 8': 'duty',
                                                  'Unnamed: 9': 'capacity_percentage'})
        regression2 = regression2.drop([23, 24])
        regression2 = regression2.reset_index(drop=True)
        self.container['regression2'] = regression2

        regression3 = df.iloc[39:46]
        regression3 = regression3.drop(columns={'Unnamed: 0', 'Unnamed: 1',
                                                'Unnamed: 6', 'Unnamed: 7',
                                                'Unnamed: 8', 'Unnamed: 9',
                                                'Unnamed: 10', 'Unnamed: 11',
                                                'Unnamed: 12', 'Unnamed: 13',
                                                'Unnamed: 14', 'Unnamed: 15',
                                                'Unnamed: 16', 'Unnamed: 17',
                                                'Unnamed: 18'})
        regression3 = regression3.rename(columns={'Unnamed: 2': 'ambient_temp',
                                                  'Unnamed: 3': 'COSP',
                                                  'Unnamed: 4': 'duty',
                                                  'Unnamed: 5': 'capacity_percentage'})
        regression3 = regression3.reset_index(drop=True)
        self.container['regression3'] = regression3

        regression4 = df.iloc[39:46]
        regression4 = regression4.drop(columns={'Unnamed: 0', 'Unnamed: 1',
                                                'Unnamed: 2', 'Unnamed: 3',
                                                'Unnamed: 4', 'Unnamed: 5',
                                                'Unnamed: 10', 'Unnamed: 11',
                                                'Unnamed: 12', 'Unnamed: 13',
                                                'Unnamed: 14', 'Unnamed: 15',
                                                'Unnamed: 16', 'Unnamed: 17',
                                                'Unnamed: 18'})
        regression4 = regression4.rename(columns={'Unnamed: 6': 'ambient_temp',
                                                  'Unnamed: 7': 'COSP',
                                                  'Unnamed: 8': 'duty',
                                                  'Unnamed: 9': 'capacity_percentage'})
        regression4 = regression4.reset_index(drop=True)
        self.container['regression4'] = regression4
