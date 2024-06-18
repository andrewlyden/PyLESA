"""fixed order controller

this script initialises other class objects
which are used to calculate the means by
which the supply, demand and storage operate

the fixed order control contains a set order of operations
which are followed
"""
import logging
import pandas as pd
from pathlib import Path
import numpy as np
import pickle
from tqdm import tqdm

from .. import initialise_classes
from ..io import inputs
from ..constants import OUTDIR
from ..heat.models import PerformanceValue
from ..heat.enums import Fuel

LOG = logging.getLogger(__name__)

class FixedOrder(object):

    def __init__(self, root: Path, subname: str):

        self.root = Path(root).resolve()
        self.subname = subname

        classes = initialise_classes.init(self.root, subname)
        self.myUserWindturbine = classes['myUserWindturbine']
        self.myDatabaseWindturbine = classes['myDatabaseWindturbine']
        self.myPV = classes['myPV']
        self.myHotWaterTank = classes['myHotWaterTank']
        self.myHeatPump = classes['myHeatPump']
        self.myElectricalStorage = classes['myElectricalStorage']
        self.myAux = classes['myAux']

        myInputs = inputs.Inputs(self.root, subname)

        dem = myInputs.demands()
        self.source_temp = dem['source_temp']
        self.flow_temp = dem['flow_temp_DH']
        self.elec_demand = dem['elec_demand']
        self.heat_demand = dem['heat_demand']
        self.return_temp = dem['return_temp_DH']
        self.source_delta_t = dem['source_delta_t']

        self.myGrid = classes['myGrid']
        self.import_price = self.myGrid.import_cost_series()
        self.export_price = self.myGrid.export

        controller_inputs = myInputs.controller()
        self.import_setpoint = controller_inputs['import_setpoint']
        self.fixed_order_info = controller_inputs['fixed_order_info']

    def run_timesteps(self, first_hour, timesteps):
        """run fixed order controller

        Arguments:
            timesteps {int} -- number of timesteps to run

        Returns:
            dataframe -- outputs for each timestep
        """

        # calculate renewable generation
        wind_user = self.myUserWindturbine.user_power()['wind_user']
        wind_data = (
            self.myDatabaseWindturbine.database_power()['wind_database'])
        wind = wind_user + wind_data
        PV = self.myPV.power_output()

        renewable_generation = wind_user + wind_data + PV
        # create instance of Check class
        myCheck = CheckFunctions(
            renewable_generation, self.elec_demand, self.heat_demand)
        # the electricity match metrics are performed over the entire year
        elec_match = myCheck.electrical_surplus_deficit()
        match = elec_match['match']
        surplus = elec_match['surplus']
        deficit = elec_match['deficit']
        RES_used_demand = elec_match['RES_used']

        # heat pump performance over the year
        hp_performance = self.myHeatPump.performance()

        # node temperatures and simulation outputs updated every timestep
        nodes_temp_list = []
        soc_list = []
        results = []

        # can run number of timesteps up to 8760
        # final hour is from first hour plus number of timesteps
        final_hour = first_hour + timesteps
        if final_hour > 8760:
            msg = f'The final timestep is {final_hour} which is beyond the end of the year (8760)'
            LOG.error(msg)
            raise ValueError(msg)

        # run controller for each timestep
        for timestep in tqdm(
                range(first_hour, final_hour),
                desc=f"Solving: {self.subname}",
                leave=False
            ):
            heat_demand = self.heat_demand[timestep]
            source_temp = self.source_temp[timestep]
            flow_temp = self.flow_temp[timestep]
            import_price = self.import_price[timestep]

            # node temperatures are from previous calc or initial
            if timestep == first_hour:
                nodes_temp_list.append(
                    self.myHotWaterTank.init_temps(self.return_temp))
                nodes_temp = nodes_temp_list[0]
                soc_list.append(
                    self.myElectricalStorage.init_state())
                soc = soc_list[0]
            else:
                nodes_temp = nodes_temp_list[timestep - first_hour]
                soc = soc_list[timestep - first_hour]

            # run for either above or below setpoint
            if import_price > self.import_setpoint:
                run = self.above_setpoint(
                    timestep, surplus[timestep], deficit[timestep],
                    match[timestep], nodes_temp, soc, hp_performance[timestep],
                    myCheck, heat_demand, source_temp, flow_temp, import_price)
            elif import_price <= self.import_setpoint:
                run = self.below_setpoint(
                    timestep, surplus[timestep], deficit[timestep],
                    match[timestep], nodes_temp, soc, hp_performance[timestep],
                    myCheck, heat_demand, source_temp, flow_temp, import_price)

            # complete the set of results
            run['RES']['elec_demand'] = RES_used_demand[timestep]
            run['elec_demand']['RES'] = RES_used_demand[timestep]
            run['RES']['generation_total'] = renewable_generation[timestep]
            run['RES']['wind'] = wind[timestep]
            run['RES']['PV'] = PV[timestep]
            run['RES']['HP'] = run['HP']['elec_RES_usage']
            run['RES']['aux'] = (
                run['aux']['RES_to_demand'] +
                run['aux']['RES_to_TS'])

            run['elec_demand']['elec_demand'] = self.elec_demand[timestep]
            run['heat_demand']['heat_demand'] = heat_demand

            # add to list of results
            results.append(run)
            # update node temperature and soc for next timestep run
            nodes_temp_list.append(
                run['TS']['final_nodes_temp'])
            soc_list.append(
                run['ES']['final_soc'])

        # write the outputs to a pickle
        file = self.root / OUTDIR / self.subname / 'outputs.pkl'
        with open(file, 'wb') as output_file:
            pickle.dump(results, output_file,
                        protocol=pickle.HIGHEST_PROTOCOL)

    def above_setpoint(self, timestep, surplus, deficit, match,
                       nodes_temp, soc, hp_performance, myCheck,
                       heat_demand, source_temp, flow_temp, import_price):

        results = self.set_of_results()

        results['grid']['surplus'] = surplus
        results['grid']['deficit'] = deficit
        results['grid']['match'] = surplus - deficit
        results['grid']['import_price'] = self.import_price[timestep]
        results['HP']['cop'] = hp_performance.cop
        results['HP']['duty'] = hp_performance.duty

        order_above_setpoint = self.fixed_order_info['order_above_setpoint']
        key = self.process_key()['above']

        checks = {'elec_unmet': deficit,
                  'heat_unmet': heat_demand,
                  'RES_left': surplus,
                  'hp_usage': 0.0,
                  'ts_discharge': 0.0,
                  'ts_charge': 0.0,
                  'soc': soc,
                  'aux_left': np.amax(self.heat_demand.values)
                  }

        for number in range(len(order_above_setpoint)):

            process = key[order_above_setpoint[number]]
            checks, results = self.run_process(
                results, checks, process, timestep, surplus,
                deficit, match, nodes_temp, soc, hp_performance,
                myCheck, heat_demand, source_temp, flow_temp,
                import_price)

        # complete results with additional calculations
        # heat pump results

        results['heat_demand']['HP'] = (
            results['heat_demand']['HP_RES'] +
            results['heat_demand']['HP_import'] +
            results['heat_demand']['HP_ES'])

        results['HP']['heat_to_heat_demand'] = (
            results['HP']['heat_from_RES_to_demand'] +
            results['HP']['heat_from_import_to_demand'] +
            results['HP']['heat_from_ES_to_demand'])
        results['HP']['heat_to_TS'] = (
            results['HP']['heat_from_RES_to_TS'] +
            results['HP']['heat_from_import_to_TS'])
        results['HP']['heat_total_output'] = (
            results['HP']['heat_to_heat_demand'] +
            results['HP']['heat_to_TS'])

        results['HP']['elec_RES_usage'] = (
            results['HP']['elec_from_RES_to_demand'] +
            results['HP']['elec_from_RES_to_TS'])
        results['HP']['elec_import_usage'] = (
            results['HP']['elec_from_import_to_demand'] +
            results['HP']['elec_from_import_to_TS'])
        results['HP']['elec_total_usage'] = (
            results['HP']['elec_RES_usage'] +
            results['HP']['elec_import_usage'])

        # TS results
        results['TS']['HP_to_TS'] = (
            results['TS']['HP_from_RES_to_TS'] +
            results['TS']['HP_from_import_to_TS'])
        results['TS']['charging_total'] = (
            results['TS']['HP_to_TS'] +
            results['TS']['aux_to_TS'])

        # AUX results
        results['aux']['demand'] = (
            results['aux']['RES_to_demand'] +
            results['aux']['RES_to_TS'] +
            results['heat_demand']['aux'])
        results['heat_demand']['aux'] = (
            results['heat_demand']['aux'] +
            results['aux']['RES_to_demand'])
        results['aux']['usage'] = self.myAux.fuel_usage(
            results['aux']['demand'])
        if self.myAux.fuel == Fuel.ELECTRIC:
            aux_price = results['grid']['import_price']
            density = 0.0
        else:
            aux_price = self.myAux.cost
            density = self.myAux.energy_density
        results['aux']['cost'] = (
            aux_price *
            (results['aux']['demand'] -
             results['aux']['RES_to_demand'] -
             results['aux']['RES_to_TS']))
        results['aux']['mass'] = density * results['aux']['usage']

        if self.myHotWaterTank.capacity == 0:
            final_nodes_temp = nodes_temp

        else:
            # update new nodes temperatures
            # check if charging or discharging
            ts_match = checks['ts_charge'] - checks['ts_discharge']
            if ts_match > 0:
                state = 'charging'
            elif ts_match < 0:
                state = 'discharging'
            elif ts_match == 0:
                state = 'standby'
            thermal_output = (
                results['HP']['heat_total_output'] +
                results['aux']['demand'])
            next_nodes_temp = self.myHotWaterTank.new_nodes_temp(
                state, nodes_temp, source_temp, self.source_delta_t,
                flow_temp, self.return_temp, thermal_output,
                heat_demand, timestep)
            final_nodes_temp = next_nodes_temp[- 1]
            # final_nodes_temp = [round(elem, 0) for elem in final_nodes_temp]

        results['TS']['final_nodes_temp'] = final_nodes_temp

        # ES results
        results['ES']['charging_total'] = (
            results['ES']['charging_from_RES'] +
            results['ES']['charging_from_import'])
        results['ES']['discharging_total'] = (
            results['ES']['discharging_to_demand'] +
            results['ES']['discharging_to_HP'])
        # update state of charge
        # new soc
        change_soc = (
            results['ES']['charging_total'] -
            results['ES']['discharging_total'])
        final_soc = self.myElectricalStorage.new_soc(change_soc, soc)
        results['ES']['final_soc'] = final_soc

        # grid results
        results['grid']['import_for_heat_pump_total'] = (
            results['grid']['import_for_heat_pump_to_heat_demand'] +
            results['grid']['import_for_heat_pump_to_TS'])
        if self.myAux.fuel == Fuel.ELECTRIC:
            results['grid']['total_import'] = (
                results['grid']['import_for_elec_demand'] +
                results['grid']['import_for_heat_pump_total'] +
                results['grid']['import_for_ES'] +
                results['aux']['demand'] -
                results['aux']['RES_to_demand'] -
                results['aux']['RES_to_TS'])
        else:
            results['grid']['total_import'] = (
                results['grid']['import_for_elec_demand'] +
                results['grid']['import_for_heat_pump_total'] +
                results['grid']['import_for_ES'])
        # this is in pounds
        # divide by 1000 because import price in pound/MWh
        # total import is in kWH
        results['grid']['import_costs'] = (
            results['grid']['total_import'] *
            results['grid']['import_price'] / 1000)
        results['grid']['export_income'] = (
            results['grid']['total_export'] *
            self.export_price / 1000)
        results['grid']['cashflow'] = (
            results['grid']['export_income'] -
            results['grid']['import_costs'])

        # IF HEAT PUMP THRESHOLD NOT MET
        # RUN HEAT PUMP AT MINIMUM THRESHOLD IF AVAILABLE CAPACITY
        # REMOVE AUX DEMAND
        # CHARGE EXCESS TO STORAGE
        # IF NOT AVAILABLE CAP THEN DONT RUN HP
        min_out = (self.myHeatPump.minimum_output *
                   self.myHeatPump.minimum_runtime / 60 /
                   100.0 * hp_performance.duty)
        hp_usage = results['HP']['heat_total_output']

        # need to change results if threshold not met
        if hp_usage < min_out and hp_usage > 0.1:
            # new charge is the difference between
            # original hp usage and minimum output
            HP_increase = min_out - hp_usage
            # what if not enough space in thermal store
            state = 'charging'
            tank_charge_left = (self.myHotWaterTank.max_energy_in_out(
                state, nodes_temp, source_temp,
                flow_temp, self.return_temp, timestep) +
                checks['ts_discharge'] -
                checks['ts_charge'])
            if HP_increase > tank_charge_left:
                # set all heat pump usage to zero
                results['HP']['heat_total_output'] = 0.0
                results['HP']['heat_to_heat_demand'] = 0.0
                results['HP']['heat_to_TS'] = 0.0
                results['HP']['heat_from_RES_to_demand'] = 0.0
                results['HP']['heat_from_RES_to_TS'] = 0.0
                results['HP']['heat_from_import_to_demand'] = 0.0
                results['HP']['heat_from_import_to_TS'] = 0.0
                results['HP']['heat_from_ES_to_demand'] = 0.0
                results['HP']['elec_total_usage'] = 0.0
                results['HP']['elec_RES_usage'] = 0.0
                results['HP']['elec_import_usage'] = 0.0
                results['HP']['elec_from_RES_to_demand'] = 0.0
                results['HP']['elec_from_RES_to_TS'] = 0.0
                results['HP']['elec_from_import_to_demand'] = 0.0
                results['HP']['elec_from_import_to_TS'] = 0.0
                results['HP']['elec_from_ES_to_demand'] = 0.0

                results['heat_demand']['HP'] = 0.0
                results['heat_demand']['HP_RES'] = 0.0
                results['heat_demand']['HP_import'] = 0.0
                results['heat_demand']['HP_ES'] = 0.0

                results['RES']['HP_to_heat_demand'] = 0.0
                results['RES']['HP_to_TS'] = 0.0

                results['TS']['HP_to_TS'] = 0.0
                results['TS']['HP_from_RES_to_TS'] = 0.0
                results['TS']['HP_from_import_to_TS'] = 0.0
                if self.myHotWaterTank.capacity == 0:
                    final_nodes_temp = nodes_temp
                else:
                    # update new nodes temperatures
                    # check if charging or discharging
                    state = 'discharging'
                    thermal_output = 0.0
                    next_nodes_temp = self.myHotWaterTank.new_nodes_temp(
                        state, nodes_temp, source_temp, self.source_delta_t,
                        flow_temp, self.return_temp, thermal_output,
                        heat_demand, timestep)
                    final_nodes_temp = next_nodes_temp[-1]
                    results['TS']['final_nodes_temp'] = final_nodes_temp

                # set the auxiliary to meet the remaining demand
                results['aux']['demand'] = (
                    heat_demand -
                    results['TS']['discharging_total'])

            else:
                # add on charging from imports
                results['HP']['heat_from_import_to_TS'] += HP_increase
                results['HP']['heat_to_TS'] += HP_increase
                results['HP']['heat_total_output'] += HP_increase
                results['HP']['elec_total_usage'] += (
                    HP_increase / results['HP']['cop'])
                results['HP']['elec_import_usage'] += (
                    HP_increase / results['HP']['cop'])
                results['HP']['elec_from_import_to_TS'] += (
                    HP_increase / results['HP']['cop'])
                results['TS']['HP_to_TS'] += HP_increase
                results['TS']['HP_from_import_to_TS'] += HP_increase

                if self.myHotWaterTank.capacity == 0:
                    final_nodes_temp = nodes_temp
                else:
                    # update new nodes temperatures
                    # check if charging or discharging
                    ts_match += HP_increase
                    if ts_match > 0:
                        state = 'charging'
                    elif ts_match < 0:
                        state = 'discharging'
                    elif ts_match == 0:
                        state = 'standby'
                    thermal_output = results['HP']['heat_total_output']
                    next_nodes_temp = self.myHotWaterTank.new_nodes_temp(
                        state, nodes_temp, source_temp, self.source_delta_t,
                        flow_temp, self.return_temp, thermal_output,
                        heat_demand, timestep)
                    final_nodes_temp = next_nodes_temp[-1]
                    results['TS']['final_nodes_temp'] = final_nodes_temp

        return results

    def below_setpoint(self, timestep, surplus, deficit, match,
                       nodes_temp, soc, hp_performance, myCheck,
                       heat_demand, source_temp, flow_temp, import_price):

        results = self.set_of_results()

        results['grid']['surplus'] = surplus
        results['grid']['deficit'] = deficit
        results['grid']['match'] = surplus - deficit
        results['grid']['import_price'] = self.import_price[timestep]
        results['grid']['export_price'] = self.export_price
        results['HP']['cop'] = hp_performance.cop
        results['HP']['duty'] = hp_performance.duty

        order_below_setpoint = self.fixed_order_info['order_below_setpoint']
        key = self.process_key()['below']

        checks = {'elec_unmet': deficit,
                  'heat_unmet': heat_demand,
                  'RES_left': surplus,
                  'hp_usage': 0.0,
                  'ts_discharge': 0.0,
                  'ts_charge': 0.0,
                  'soc': soc,
                  'aux_left': np.amax(self.heat_demand.values)
                  }

        for number in range(len(order_below_setpoint)):

            process = key[order_below_setpoint[number]]
            checks, results = self.run_process(
                results, checks, process, timestep, surplus,
                deficit, match, nodes_temp, soc, hp_performance,
                myCheck, heat_demand, source_temp, flow_temp,
                import_price)

        # heat pump results
        results['HP']['heat_to_heat_demand'] = (
            results['HP']['heat_from_RES_to_demand'] +
            results['HP']['heat_from_import_to_demand'] +
            results['HP']['heat_from_ES_to_demand'])
        results['HP']['heat_to_TS'] = (
            results['HP']['heat_from_RES_to_TS'] +
            results['HP']['heat_from_import_to_TS'])
        results['HP']['heat_total_output'] = (
            results['HP']['heat_to_heat_demand'] +
            results['HP']['heat_to_TS'])

        # complete results with additional calculations

        # heat demand results
        results['heat_demand']['HP'] = (
            results['heat_demand']['HP_RES'] +
            results['heat_demand']['HP_import'] +
            results['heat_demand']['HP_ES'])

        # HP electrica usage
        results['HP']['elec_RES_usage'] = (
            results['HP']['elec_from_RES_to_demand'] +
            results['HP']['elec_from_RES_to_TS'])
        results['HP']['elec_import_usage'] = (
            results['HP']['elec_from_import_to_demand'] +
            results['HP']['elec_from_import_to_TS'])
        results['HP']['elec_total_usage'] = (
            results['HP']['elec_RES_usage'] +
            results['HP']['elec_import_usage'])

        # AUX results
        results['aux']['demand'] = (
            results['aux']['RES_to_demand'] +
            results['aux']['RES_to_TS'] +
            results['heat_demand']['aux'])
        results['aux']['usage'] = self.myAux.fuel_usage(
            results['aux']['demand'])
        if self.myAux.fuel == Fuel.ELECTRIC:
            aux_price = results['grid']['import_price']
            density = 0.0
        else:
            aux_price = self.myAux.cost
            density = self.myAux.energy_density
        results['aux']['cost'] = (
            aux_price *
            (results['aux']['demand'] -
             results['aux']['RES_to_demand'] -
             results['aux']['RES_to_TS']))
        results['aux']['mass'] = density * results['aux']['usage']

        # TS results
        results['TS']['HP_to_TS'] = (
            results['TS']['HP_from_RES_to_TS'] +
            results['TS']['HP_from_import_to_TS'])
        results['TS']['charging_total'] = (
            results['TS']['HP_to_TS'] +
            results['TS']['aux_to_TS'])

        if self.myHotWaterTank.capacity == 0:
            final_nodes_temp = nodes_temp
        else:
            # update new nodes temperatures
            # check if charging or discharging
            ts_match = round(checks['ts_charge'] - checks['ts_discharge'], 1)
            if ts_match > 0:
                state = 'charging'
            elif ts_match < 0:
                state = 'discharging'
            elif ts_match == 0:
                state = 'standby'
            thermal_output = (
                results['HP']['heat_total_output'] +
                results['aux']['demand'])

            next_nodes_temp = self.myHotWaterTank.new_nodes_temp(
                state, nodes_temp, source_temp, self.source_delta_t,
                flow_temp, self.return_temp, thermal_output,
                heat_demand, timestep)
            final_nodes_temp = next_nodes_temp[-1]

        results['TS']['final_nodes_temp'] = final_nodes_temp

        # ES results
        results['ES']['charging_total'] = (
            results['ES']['charging_from_RES'] +
            results['ES']['charging_from_import'])
        results['ES']['discharging_total'] = (
            results['ES']['discharging_to_demand'] +
            results['ES']['discharging_to_HP'])
        # update state of charge
        # new soc
        change_soc = (
            results['ES']['charging_total'] -
            results['ES']['discharging_total'])
        final_soc = self.myElectricalStorage.new_soc(change_soc, soc)
        results['ES']['final_soc'] = final_soc

        # grid results
        results['grid']['import_for_heat_pump_total'] = (
            results['grid']['import_for_heat_pump_to_heat_demand'] +
            results['grid']['import_for_heat_pump_to_TS'])
        if self.myAux.fuel == Fuel.ELECTRIC:
            results['grid']['total_import'] = (
                results['grid']['import_for_elec_demand'] +
                results['grid']['import_for_heat_pump_total'] +
                results['grid']['import_for_ES'] +
                results['aux']['demand'] -
                results['aux']['RES_to_demand'] -
                results['aux']['RES_to_TS'])
        else:
            results['grid']['total_import'] = (
                results['grid']['import_for_elec_demand'] +
                results['grid']['import_for_heat_pump_total'] +
                results['grid']['import_for_ES'])
        # this is in pounds
        # divide by 1000 because import price in pound/MWh
        # total import is in kWH
        results['grid']['import_costs'] = (
            results['grid']['total_import'] *
            results['grid']['import_price'] / 1000)
        results['grid']['export_income'] = (
            results['grid']['total_export'] *
            self.export_price / 1000)
        results['grid']['cashflow'] = (
            results['grid']['export_income'] -
            results['grid']['import_costs'])

        # for below setpoint only
        results['grid']['import_below_setpoint'] = (
            results['grid']['total_import'])

        # IF HEAT PUMP THRESHOLD NOT MET
        # RUN HEAT PUMP AT MINIMUM THRESHOLD IF AVAILABLE CAPACITY
        # REMOVE AUX DEMAND
        # CHARGE EXCESS TO STORAGE
        # IF NOT AVAILABLE CAP THEN DONT RUN HP
        min_out = (self.myHeatPump.minimum_output *
                   self.myHeatPump.minimum_runtime / 60 /
                   100.0 * hp_performance.duty)
        hp_usage = results['HP']['heat_total_output']

        # need to change results if threshold not met
        if hp_usage < min_out and hp_usage > 0:
            # new charge is the difference between
            # original hp usage and minimum output
            HP_increase = min_out - hp_usage
            # what if not enough space in thermal store
            # remove the existing charging/discharging
            state = 'charging'
            tank_charge_left = (self.myHotWaterTank.max_energy_in_out(
                state, nodes_temp, source_temp, flow_temp,
                self.return_temp, timestep) +
                checks['ts_discharge'] -
                checks['ts_charge'])
            
            if HP_increase > tank_charge_left:
                # set all heat pump usage to zero
                results['HP']['heat_total_output'] = 0.0
                results['HP']['heat_to_heat_demand'] = 0.0
                results['HP']['heat_to_TS'] = 0.0
                results['HP']['heat_from_RES_to_demand'] = 0.0
                results['HP']['heat_from_RES_to_TS'] = 0.0
                results['HP']['heat_from_import_to_demand'] = 0.0
                results['HP']['heat_from_import_to_TS'] = 0.0
                results['HP']['heat_from_ES_to_demand'] = 0.0
                results['HP']['elec_total_usage'] = 0.0
                results['HP']['elec_RES_usage'] = 0.0
                results['HP']['elec_import_usage'] = 0.0
                results['HP']['elec_from_RES_to_demand'] = 0.0
                results['HP']['elec_from_RES_to_TS'] = 0.0
                results['HP']['elec_from_import_to_demand'] = 0.0
                results['HP']['elec_from_import_to_TS'] = 0.0
                results['HP']['elec_from_ES_to_demand'] = 0.0

                results['heat_demand']['HP'] = 0.0
                results['heat_demand']['HP_RES'] = 0.0
                results['heat_demand']['HP_import'] = 0.0
                results['heat_demand']['HP_ES'] = 0.0

                results['RES']['HP_to_heat_demand'] = 0.0
                results['RES']['HP_to_TS'] = 0.0

                results['TS']['HP_to_TS'] = 0.0
                results['TS']['HP_from_RES_to_TS'] = 0.0
                results['TS']['HP_from_import_to_TS'] = 0.0

                # set charging to zero
                results['TS']['charging_total'] = 0.0
                # discharge from the TS to meet demand
                results['TS']['discharging_total'] = min(
                    self.myHotWaterTank.max_energy_in_out(
                        'discharging', nodes_temp, source_temp,
                        flow_temp, self.return_temp, timestep),
                    heat_demand)

                if self.myHotWaterTank.capacity == 0:
                    final_nodes_temp = nodes_temp
                else:
                    # update new nodes temperatures
                    # check if charging or discharging
                    state = 'discharging'
                    thermal_output = 0.0
                    heat_demand = results['TS']['discharging_total']
                    next_nodes_temp = self.myHotWaterTank.new_nodes_temp(
                        state, nodes_temp, source_temp, self.source_delta_t,
                        flow_temp, self.return_temp, thermal_output,
                        heat_demand, timestep)
                    final_nodes_temp = next_nodes_temp[-1]
                    results['TS']['final_nodes_temp'] = final_nodes_temp

                # set the auxiliary to meet the remaining demand
                results['aux']['demand'] = (
                    heat_demand -
                    results['TS']['discharging_total'])

            else:
                # add on charging from imports
                results['HP']['heat_from_import_to_TS'] += HP_increase
                results['HP']['heat_to_TS'] += HP_increase
                results['HP']['heat_total_output'] += HP_increase
                results['HP']['elec_total_usage'] += (
                    HP_increase / results['HP']['cop'])
                results['HP']['elec_import_usage'] += (
                    HP_increase / results['HP']['cop'])
                results['HP']['elec_from_import_to_TS'] += (
                    HP_increase / results['HP']['cop'])
                results['TS']['HP_to_TS'] += HP_increase
                results['TS']['HP_from_import_to_TS'] += HP_increase

                if self.myHotWaterTank.capacity == 0:
                    final_nodes_temp = nodes_temp
                else:
                    # update new nodes temperatures
                    # check if charging or discharging
                    ts_match += HP_increase
                    if ts_match > 0:
                        state = 'charging'
                    elif ts_match < 0:
                        state = 'discharging'
                    elif ts_match == 0:
                        state = 'standby'
                    thermal_output = results['HP']['heat_total_output']
                    next_nodes_temp = self.myHotWaterTank.new_nodes_temp(
                        state, nodes_temp, source_temp, self.source_delta_t,
                        flow_temp, self.return_temp, thermal_output,
                        heat_demand, timestep)
                    final_nodes_temp = next_nodes_temp[- 1]
                    results['TS']['final_nodes_temp'] = final_nodes_temp

        return results

    def run_process(self, results, checks, process, timestep, surplus,
                    deficit, match, nodes_temp, soc, hp_performance,
                    myCheck, heat_demand, source_temp, flow_temp,
                    import_price, heat_pump_output=None):

        elec_unmet = checks['elec_unmet']
        heat_unmet = checks['heat_unmet']
        RES_left = checks['RES_left']
        hp_usage = checks['hp_usage']
        ts_discharge = checks['ts_discharge']
        ts_charge = checks['ts_charge']
        soc = checks['soc']
        aux_left = checks['aux_left']

        if process == 'ES to demand':
            r = self.ES_to_demand(
                elec_unmet, soc)
            results['elec_demand']['ES'] = r
            results['ES']['discharging_to_demand'] = r

        elif process == 'Import to demand':
            r = self.import_to_demand(elec_unmet)
            results['elec_demand']['import'] = r
            results['grid']['import_for_elec_demand'] = r

        elif process == 'HP RES to demand':
            r = self.HP_RES_to_demand(
                hp_usage, RES_left, hp_performance, heat_unmet)
            results['heat_demand']['HP_RES'] = r['h']
            results['RES']['HP_to_heat_demand'] = r['e']
            results['HP']['heat_from_RES_to_demand'] = r['h']
            results['HP']['elec_from_RES_to_demand'] = r['e']

        elif process == 'EAUX RES to demand':
            r = self.EAUX_RES_to_demand(
                aux_left, RES_left, heat_unmet)
            results['aux']['RES_to_demand'] = r

        elif process == 'HP import to demand':
            r = self.HP_import_to_demand(
                hp_usage, heat_unmet, hp_performance,
                heat_pump_output)
            results['heat_demand']['HP_import'] = r['h']
            results['grid']['import_for_heat_pump_to_heat_demand'] = r['e']
            results['HP']['heat_from_import_to_demand'] = r['h']
            results['HP']['elec_from_import_to_demand'] = r['e']

        elif process == 'TS to demand':
            r = self.TS_to_demand(
                heat_unmet, nodes_temp, source_temp, flow_temp,
                timestep, ts_discharge, ts_charge)
            results['heat_demand']['TS'] = r
            results['TS']['discharging_total'] = r

        elif process == 'ES to HP to demand':
            r = self.ES_to_HP_to_demand(
                soc, hp_performance, heat_unmet, hp_usage)
            results['heat_demand']['HP_ES'] = r['h']
            results['ES']['discharging_to_HP'] = r['e']
            results['HP']['heat_from_ES_to_demand'] = r['h']
            results['HP']['elec_from_ES_to_demand'] = r['e']

        elif process == 'AUX to demand':
            r = self.aux_to_demand(
                heat_unmet)
            results['heat_demand']['aux'] = r

        elif process == 'HP RES to TS':
            r = self.HP_RES_to_TS(
                RES_left, hp_performance, hp_usage, heat_demand,
                nodes_temp, source_temp, flow_temp, timestep,
                ts_discharge, ts_charge)
            results['RES']['HP_to_TS'] = r['e']
            results['HP']['heat_from_RES_to_TS'] = r['h']
            results['HP']['elec_from_RES_to_TS'] = r['e']
            results['TS']['HP_from_RES_to_TS'] = r['h']

        elif process == 'EAUX RES to TS':
            r = self.EAUX_RES_to_TS(
                aux_left, RES_left, nodes_temp, source_temp,
                flow_temp, timestep, ts_discharge, ts_charge)
            results['aux']['RES_to_TS'] = r
            results['TS']['aux_to_TS'] = r

        elif process == 'HP import to TS':
            r = self.HP_import_to_TS(
                hp_performance, hp_usage, nodes_temp, source_temp,
                flow_temp, timestep, ts_discharge, ts_charge)
            results['grid']['import_for_heat_pump_to_TS'] = r['e']
            results['HP']['heat_from_import_to_TS'] = r['h']
            results['HP']['elec_from_import_to_TS'] = r['e']
            results['TS']['HP_from_import_to_TS'] = r['h']

        elif process == 'RES to ES':
            r = self.RES_to_ES(
                RES_left, soc)
            results['RES']['ES'] = r
            results['ES']['charging_from_RES'] = r

        elif process == 'Import to ES':
            r = self.import_to_ES(
                soc)
            results['grid']['import_for_ES'] = r
            results['ES']['charging_from_import'] = r

        elif process == 'RES to export':
            r = self.RES_to_export(
                RES_left)
            results['RES']['export'] = r
            results['grid']['total_export'] = r

        elec_unmet_process = ['ES to demand', 'Import to demand']
        heat_unmet_process = ['HP RES to demand', 'TS to demand',
                              'HP import to demand', 'ES to HP to demand',
                              'AUX to demand', 'EAUX RES to demand']
        RES_left_process = ['HP RES to demand', 'HP RES to TS',
                            'RES to ES', 'RES to export',
                            'EAUX RES to demand', 'EAUX RES to TS']
        hp_usage_process = ['HP RES to demand', 'HP RES to TS',
                            'HP import to demand', 'HP import to TS']
        ts_discharge_process = ['TS to demand']
        ts_charge_process = ['HP RES to TS', 'HP import to TS',
                             'EAUX RES to TS']
        soc_process = ['ES to demand', 'ES to HP to demand',
                       'RES to ES', 'Import to ES']
        aux_process = ['EAUX RES to demand', 'AUX to demand',
                       'EAUX RES to TS']

        if process in elec_unmet_process:
            checks['elec_unmet'] -= r
        if process in heat_unmet_process:
            # heat pump has two results
            # this accounts for this
            try:
                checks['heat_unmet'] -= r['h']
            except:
                checks['heat_unmet'] -= r
        if process in RES_left_process:
            try:
                checks['RES_left'] -= r['e']
            except:
                checks['RES_left'] -= r

        if process in hp_usage_process:
            checks['hp_usage'] += r['h']
        if process in ts_discharge_process:
            checks['ts_discharge'] += r
        if process in ts_charge_process:
            try:
                checks['ts_charge'] += r['h']
            except:
                checks['ts_charge'] += r
        if process in soc_process:
            if process == 'ES to demand':
                r = -r
            elif process == 'ES to HP to demand':
                r = -r['e']
            checks['soc'] += r
        if process in aux_process:
            checks['aux_left'] -= r

        return checks, results

    def process_key(self):

        above = {1: 'RES to demand',
                 2: 'ES to demand',
                 3: 'Import to demand',
                 4: 'HP RES to demand',
                 5: 'EAUX RES to demand',
                 6: 'TS to demand',
                 7: 'ES to HP to demand',
                 8: 'HP import to demand',
                 9: 'AUX to demand',
                 10: 'HP RES to TS',
                 11: 'EAUX RES to TS',
                 12: 'RES to ES',
                 13: 'RES to export'}

        below = {1: 'RES to demand',
                 2: 'Import to demand',
                 3: 'ES to demand',
                 4: 'HP RES to demand',
                 5: 'EAUX RES to demand',
                 6: 'HP import to demand',
                 7: 'TS to demand',
                 8: 'ES to HP to demand',
                 9: 'AUX to demand',
                 10: 'HP RES to TS',
                 11: 'EAUX RES to TS',
                 12: 'HP import to TS',
                 13: 'RES to ES',
                 14: 'Import to ES',
                 15: 'RES to export'}

        return {'above': above, 'below': below}

    def set_of_results(self):

        elec_demand = {'RES': 0.0,  #
                       'ES': 0.0,  #
                       'import': 0.0,  #
                       'elec_demand': 0.0  #
                       }

        heat_demand = {'HP': 0.0,  #
                       'HP_RES': 0.0,  #
                       'HP_import': 0.0,  #
                       'HP_ES': 0.0,  #
                       'TS': 0.0,  #
                       'aux': 0.0,  #
                       'heat_demand': 0.0  #
                       }

        RES = {'generation_total': 0.0,  #
               'wind': 0.0,  #
               'PV': 0.0,  #
               'elec_demand': 0.0,  #
               'HP': 0.0,  #
               'ES': 0.0,  #
               'export': 0.0,  #
               'aux': 0.0
               }

        HP = {'heat_total_output': 0.0,  #
              'heat_to_heat_demand': 0.0,  #
              'heat_to_TS': 0.0,  #
              'heat_from_RES_to_demand': 0.0,  #
              'heat_from_RES_to_TS': 0.0,  #
              'heat_from_import_to_demand': 0.0,  #
              'heat_from_import_to_TS': 0.0,  #
              'heat_from_ES_to_demand': 0.0,  #
              'elec_total_usage': 0.0,  #
              'elec_RES_usage': 0.0,  #
              'elec_import_usage': 0.0,  #
              'elec_from_RES_to_demand': 0.0,  #
              'elec_from_RES_to_TS': 0.0,  #
              'elec_from_import_to_demand': 0.0,  #
              'elec_from_import_to_TS': 0.0,  #
              'elec_from_ES_to_demand': 0.0,  #
              'cop': 0.0,  #
              'duty': 0.0  #
              }

        TS = {'charging_total': 0.0,  #
              'discharging_total': 0.0,  #
              'HP_to_TS': 0.0,  #
              'HP_from_RES_to_TS': 0.0,  #
              'HP_from_import_to_TS': 0.0,  #
              'aux_to_TS': 0.0,  #
              'aux_from_RES_to_TS': 0.0,  #
              'aux_from_import_to_TS': 0.0,  #
              'final_nodes_temp': 0.0  #
              }

        aux = {'demand': 0.0,  #
               'usage': 0.0,  #
               'mass': 0.0,  #
               'cost': 0.0,  #
               'RES_to_demand': 0.0,  #
               'RES_to_TS': 0.0  #
               }

        ES = {'charging_total': 0.0,  #
              'discharging_total': 0.0,  #
              'discharging_to_demand': 0.0,  #
              'discharging_to_HP': 0.0,  #
              'discharging_to_aux': 0.0,  #
              'charging_from_RES': 0.0,  #
              'charging_from_import': 0.0,  #
              'final_soc': 0.0  #
              }

        grid = {'total_import': 0.0,  #
                'total_export': 0.0,  #
                'import_for_elec_demand': 0.0,  #
                'import_for_heat_pump_total': 0.0,  #
                'import_for_heat_pump_to_heat_demand': 0.0,  #
                'import_for_heat_pump_to_TS': 0.0,  #
                'import_for_ES': 0.0,  #
                'import_below_setpoint': 0.0,  #
                'import_price': 0.0,  #
                'export_price': 0.0,  #
                'import_costs': 0.0,  #
                'export_income': 0.0,  #
                'cashflow': 0.0,  #
                'surplus': 0.0,  #
                'deficit': 0.0,  #
                'match': 0.0  #
                }

        outputs = {'elec_demand': elec_demand,
                   'heat_demand': heat_demand,
                   'RES': RES,
                   'HP': HP,
                   'TS': TS,
                   'aux': aux,
                   'ES': ES,
                   'grid': grid}

        return outputs

    def ES_to_demand(self, elec_unmet, soc):

        # DISCHARGE BATTERY TO MEET DEMAND

        # min between elec_unmet and soc
        es_discharging = min(elec_unmet, soc)

        return es_discharging

    def import_to_demand(self, elec_unmet):

        # MEET ELEC DEMAND FROM IMPORTS

        import_elec_demand = elec_unmet

        return import_elec_demand

    def HP_RES_to_demand(self, hp_usage, RES_left, hp_performance: PerformanceValue, heat_unmet):

        # USE HEAT PUMP WITH SURPLUS TO MEET HEAT DEMAND

        heat_pump_spare = (
            hp_performance.duty -
            hp_usage)

        # hpr - heat pump renewable
        hpr = self.myHeatPump.thermal_output(
            RES_left, hp_performance, heat_unmet)
        # thermal output from heat pump running on renewables
        HPtrd = min(hpr.demand, heat_pump_spare)
        # elec usage
        HPetd = self.myHeatPump.elec_usage(
            HPtrd, hp_performance)

        return {'h': HPtrd, 'e': HPetd}

    def EAUX_RES_to_demand(self, aux_left, RES_left, heat_unmet):

        if self.myAux.fuel == Fuel.ELECTRIC:

            # use up surplus with electric heater if exisitng

            aux_use = min(aux_left, RES_left, heat_unmet)

        else:
            aux_use = 0.0

        return aux_use

    def HP_import_to_demand(self, hp_usage, heat_unmet, hp_performance,
                            heat_pump_output):

        # USE HEAT PUMP WITH GRID ELECTRICITY
        # TO MEET HEAT DEMAND

        heat_pump_spare = (
            hp_performance.duty -
            hp_usage)

        # min of dem unmet and spare hp capacity
        heat_pump_import_demand = min(
            heat_unmet, heat_pump_spare)

        if self.myHeatPump.capacity == 0:
            heat_pump_import_demand = 0

        if heat_pump_output is not None:
            heat_pump_import_demand = (
                heat_pump_output - hp_usage)

        # elec usage
        elec = self.myHeatPump.elec_usage(
            heat_pump_import_demand, hp_performance)

        return {'h': heat_pump_import_demand, 'e': elec}

    def TS_to_demand(self, heat_unmet, nodes_temp, source_temp,
                     flow_temp, timestep, ts_discharge, ts_charge):

        # DISCHARGE FROM TANK TO MEET HEAT DEMAND

        # discharge from thermal storage to try meet heat demand
        # max discharge energy from tank
        state = 'discharging'
        max_dis = self.myHotWaterTank.max_energy_in_out(
            state, nodes_temp, source_temp,
            flow_temp,
            self.return_temp, timestep) - ts_discharge + ts_charge
        # minimum of two
        ts_discharge = min(heat_unmet, max_dis)

        return ts_discharge

    def ES_to_HP_to_demand(self, soc, hp_performance, heat_unmet, hp_usage):

        # DISCHARGE FROM ES TO RUN HEAT PUMP TO MEET DEMAND

        # max discharge from ES
        es_discharging = soc
        # max heat from heat pump running on ES discharge
        max_hp_ES = self.myHeatPump.thermal_output(
            es_discharging, hp_performance, heat_unmet)

        heat_pump_spare = (
            hp_performance.duty -
            hp_usage)

        # thermal output from heat pump running on renewables
        HP_h_es = min(max_hp_ES.demand, heat_pump_spare)
        # elec usage
        HP_e_es = self.myHeatPump.elec_usage(
            HP_h_es, hp_performance)

        return {'h': HP_h_es, 'e': HP_e_es}

    def aux_to_demand(self, heat_unmet):

        # USE FUEL BOILER TO MEET DEMAND

        return heat_unmet

    def HP_RES_to_TS(self, RES_left, hp_performance, hp_usage,
                     heat_demand, nodes_temp, source_temp,
                     flow_temp, timestep, ts_discharge, ts_charge):

        # CHARGE THERMAL STORAGE WITH HEAT PUMP DRIVEN BY SURPLUS

        duty = hp_performance.duty
        # capacity of heat pump leftover
        hp_cap_left = duty - hp_usage
        # max heat from heat pump running surplus
        hp_max_RES = RES_left * hp_performance.cop
        hp_left = min(hp_cap_left, hp_max_RES)
        # how much can be input into the hot water tank
        state = 'charging'
        tank_charge_left = self.myHotWaterTank.max_energy_in_out(
            state, nodes_temp, source_temp,
            flow_temp,
            self.return_temp, timestep) + ts_discharge - ts_charge
        # charge the hot water tank with hp driven by surplus
        # with min of hp_left or charging space in tank
        HPtrs = min(hp_left, tank_charge_left)
        # elec usage
        elec = self.myHeatPump.elec_usage(
            HPtrs, hp_performance)

        return {'h': HPtrs, 'e': elec}

    def EAUX_RES_to_TS(self, aux_left, RES_left, nodes_temp,
                       source_temp, flow_temp, timestep,
                       ts_discharge, ts_charge):

        if self.myAux.fuel == Fuel.ELECTRIC:

            # how much can be input into the hot water tank
            state = 'charging'
            tank_charge_left = self.myHotWaterTank.max_energy_in_out(
                state, nodes_temp, source_temp,
                flow_temp,
                self.return_temp, timestep) + ts_discharge - ts_charge
            aux_use = min(aux_left, RES_left, tank_charge_left)

        else:
            aux_use = 0.0

        return aux_use

    def HP_import_to_TS(self, hp_performance, hp_usage, nodes_temp,
                        source_temp, flow_temp, timestep,
                        ts_discharge, ts_charge):

        # CHARGE TANK FROM HP WITH IMPORTS

        # charge spare thermal storage capacity
        # spare heat pump capacity

        heat_pump_spare = (
            hp_performance.duty -
            hp_usage)
        # spare tank capacity
        state = 'charging'
        tank_charge_left = self.myHotWaterTank.max_energy_in_out(
            state, nodes_temp, source_temp,
            flow_temp,
            self.return_temp, timestep) + ts_discharge - ts_charge
        # charging of ts from heat pump
        ts_hp_charge_heat_imports = round(min(
            heat_pump_spare, tank_charge_left), 2)
        if self.myHeatPump.capacity == 0:
            ts_hp_charge_heat_imports = 0
        # elec usage
        elec = self.myHeatPump.elec_usage(
            ts_hp_charge_heat_imports, hp_performance)

        return {'h': ts_hp_charge_heat_imports, 'e': elec}

    def RES_to_ES(self, RES_left, soc):

        # CHARGE ELECTRIC BATTERY

        # charge battery
        charge_battery = self.myElectricalStorage.max_charging(
            RES_left, soc)

        return charge_battery

    def import_to_ES(self, soc):

        # CHARGE BATTERY WITH IMPORTS

        # calculate available capacity
        elec_store_imports = self.myElectricalStorage.charge_to_capacity(
            soc)

        return elec_store_imports

    def RES_to_export(self, RES_left):

        # EXPORT SURPLUS

        # export to grid
        elec_export = RES_left

        return elec_export


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

        """Checks if the heat demand has been met

        Args:
            timestep: a float/int of the timestep to be modelled
            heat_generated: the total heat generated up to that
                point in the flow diagram to be checked

        Returns:
            boolean, TRUE if heat demand met, FALSE if heat demand not met
       
        Raises:
            SystemExit if too much heat generated
        """
        # get the heat demand
        heat_demand = self.heat_demand[timestep]

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
        else:
            msg = f'Error in heat generation: too much heat generated ({heat_met})'
            LOG.error(msg)
            raise SystemExit(msg)

    def surplus_check(self, surplus, RES_used):
        """Checks if surplus exists at point in flow diagram

        Args:
            timestep: a float/int of the timestep to be modelled
            surplus: total surplus in the timestep
            RES_used: surplus used up to point in the flow diagram

        Returns:
            bool, TRUE if surplus exists, FALSE if surplus doesn't exist
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
        else:
            msg = f'Error in RES usage: too much RES used ({RES_leftover})'
            LOG.error(msg)
            raise SystemExit(msg)

    def deficit_check(self, deficit, elec_supplied):
        """Checks if deficit becomes surplus

        Args:
            deficit: total deficit in the timestep
            elec_supplied: surplus used up to point in the flow diagram

        Returns:
            bool, TRUE if surplus exists, FALSE if surplus doesn't exist
        """
        deficit_leftover = round(deficit, 2) - round(elec_supplied, 2)
        deficit_leftover = round(deficit_leftover, 2)

        # if greater than zero then surplus leftover
        if deficit_leftover > 0:
            return True
        # if zero then no surplus
        elif deficit_leftover == 0:
            return False
        # if something else then error
        else:
            msg = f'Error in program: deficit turned into surplus ({deficit_leftover})'
            LOG.error(msg)
            raise SystemExit(msg)
