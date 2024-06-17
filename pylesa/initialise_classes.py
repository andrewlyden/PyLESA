"""initialises all the classes

simplifies initialising all the models for use
in the control scripts
"""
import logging
import pandas as pd
from pathlib import Path
from typing import Dict

from .io import inputs
from .power import grid, renewables
from .storage import hot_water_tank, electrical_storage
from .heat import heatpump, auxiliary
from .heat.enums import ModelName

LOG = logging.getLogger(__name__)

def init(root: Path, subname: str) -> Dict[str, object]:
    """Initialise pylesa classes for use in controllers
    
    Args:
        root: root directory of simulation
        subname: name of specific parametric run configuration

    Returns:
        Dictionary of initialised objects
    """
    myInputs = inputs.Inputs(root, subname)

    # initialise instance of classes
    input_windturbine = myInputs.windturbine_user()
    input_weather = myInputs.weather()

    myUserWindturbine = renewables.Windturbine(
        turbine_name=input_windturbine['turbine_name'],
        hub_height=input_windturbine['hub_height'],
        rotor_diameter=input_windturbine['rotor_diameter'],
        multiplier=input_windturbine['multiplier'],
        nominal_power=input_windturbine['nominal_power'],
        power_curve=input_windturbine['power_curve'],
        weather_input=input_weather)

    input_windturbine = myInputs.windturbine_database()

    myDatabaseWindturbine = renewables.Windturbine(
        turbine_name=input_windturbine['turbine_name'],
        hub_height=input_windturbine['hub_height'],
        rotor_diameter=input_windturbine['rotor_diameter'],
        multiplier=input_windturbine['multiplier'],
        weather_input=input_weather)

    input_PV_model = myInputs.PV_model()

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

    ts_inputs = myInputs.hot_water_tank()

    myHotWaterTank = hot_water_tank.HotWaterTank(
        ts_inputs['capacity'],
        ts_inputs['insulation'],
        ts_inputs['location'],
        ts_inputs['number_nodes'],
        ts_inputs['dimensions'],
        ts_inputs['tank_openings'],
        ts_inputs['correction_factors'],
        air_temperature=input_weather)

    # Setup heat pump class
    inputs_basics = myInputs.heatpump_basics()
    inputs_demands = myInputs.demands()
    inputs_simple = None
    inputs_lorentz = None
    inputs_standard = None

    match inputs_basics['modelling_approach']:
        case ModelName.SIMPLE:
            inputs_simple = myInputs.heatpump_simple()
        case ModelName.LORENTZ:
            inputs_lorentz = myInputs.heatpump_lorentz()
        case ModelName.STANDARD:
            inputs_standard = myInputs.heatpump_standard_regression()
        case _:
            msg = f"Performance modelling {inputs_basics['modelling_approach']} is not valid"
            LOG.error(msg)
            raise KeyError(msg)
    
    _ambient_temp = pd.concat(
        [
            input_weather['air_temperature'],
            input_weather['water_temperature']
        ],
        axis=1
    )

    myHeatPump = heatpump.HeatPump(
        inputs_basics['heat_pump_type'],
        inputs_basics['modelling_approach'],
        inputs_basics['capacity'],
        inputs_basics['ambient_delta_t'],
        inputs_basics['minimum_runtime'],
        inputs_basics['minimum_output'],
        inputs_basics['data_input'],
        inputs_demands['source_temp'],
        inputs_demands['return_temp_DH'],
        _ambient_temp,
        simple_cop=inputs_simple,
        lorentz_inputs=inputs_lorentz,
        standard_inputs=inputs_standard
    )

    i = myInputs.electrical_storage()
    myElectricalStorage = electrical_storage.ElectricalStorage(
        i['capacity'],
        i['initial_state'],
        i['charge_max'],
        i['discharge_max'],
        i['charge_eff'],
        i['discharge_eff'],
        i['self_discharge'])

    aux_inputs = myInputs.aux()

    myAux = auxiliary.Aux(
        aux_inputs['fuel'],
        aux_inputs['efficiency'],
        aux_inputs['fuel_info'])

    grid_inputs = myInputs.grid()
    export = grid_inputs['export']
    tariff_choice = grid_inputs['tariff_choice']
    balancing_mechanism = grid_inputs['balancing_mechanism']
    grid_services = grid_inputs['grid_services']
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

    if tariff_choice == 'Flat rates':

        fr = grid_inputs['flat_rates']
        myGrid = grid.Grid(
            root, subname, export,
            tariff_choice, balancing_mechanism, grid_services,
            flat_rate=fr)

    elif tariff_choice == 'Variable periods':

        vp = grid_inputs['variable_periods']
        myGrid = grid.Grid(
            root, subname, export,
            tariff_choice, balancing_mechanism, grid_services,
            variable_periods=vp, variable_periods_year=variable_periods_year)

    elif tariff_choice == 'Time of use - WM':

        twm = grid_inputs['wholesale_market']
        myGrid = grid.Grid(
            root, subname, export,
            tariff_choice, balancing_mechanism, grid_services,
            wholesale_market=twm, premium=premium,
            maximum=maximum)

    elif tariff_choice == 'Time of use - PPA + FR':

        fr = grid_inputs['flat_rates']
        myGrid = grid.Grid(
            root, subname, export,
            tariff_choice, balancing_mechanism, grid_services,
            flat_rate=fr, lower_percent=lower_percent,
            higher_percent=higher_percent, higher_discount=higher_discount,
            lower_penalty=lower_penalty)

    elif tariff_choice == 'Time of use - PPA + WM':

        twm = grid_inputs['wholesale_market']
        myGrid = grid.Grid(
            root, subname, export,
            tariff_choice, balancing_mechanism, grid_services,
            wholesale_market=twm, premium=premium,
            maximum=maximum, lower_percent=lower_percent,
            higher_percent=higher_percent, higher_discount=higher_discount,
            lower_penalty=lower_penalty)

    elif tariff_choice == 'Time of use - PPA + VP':

        vp = grid_inputs['variable_periods']
        myGrid = grid.Grid(
            root, subname, export,
            tariff_choice, balancing_mechanism, grid_services,
            variable_periods=vp, variable_periods_year=variable_periods_year,
            lower_percent=lower_percent,
            higher_percent=higher_percent, higher_discount=higher_discount,
            lower_penalty=lower_penalty)

    dict = {'myUserWindturbine': myUserWindturbine,
            'myDatabaseWindturbine': myDatabaseWindturbine,
            'myPV': myPV,
            'myHotWaterTank': myHotWaterTank,
            'myHeatPump': myHeatPump,
            'myElectricalStorage': myElectricalStorage,
            'myAux': myAux,
            'myGrid': myGrid}

    return dict
