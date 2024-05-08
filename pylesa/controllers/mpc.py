"""mpc module

runs the control strategy MPC
"""

from gekko import GEKKO
import numpy as np
import matplotlib.pyplot as plt
from progressbar import Bar, ETA, Percentage, ProgressBar, RotatingMarker
import pickle
import os

from .. import initialise_classes, tools
from ..io import inputs


class Scheduler(object):

    def __init__(self, name, subname):

        self.name = name
        self.subname = subname

        classes = initialise_classes.init(name, subname)

        self.myUserWindturbine = classes['myUserWindturbine']
        self.myDatabaseWindturbine = classes['myDatabaseWindturbine']
        self.myPV = classes['myPV']
        self.myHotWaterTank = classes['myHotWaterTank']
        self.myHeatPump = classes['myHeatPump']
        self.myElectricalStorage = classes['myElectricalStorage']
        self.myAux = classes['myAux']

        myInputs = inputs.Inputs(name, subname)
        self.horizon = myInputs.controller()['horizon']

        dem = myInputs.demands()
        self.source_temp = dem['source_temp']
        self.flow_temp = dem['flow_temp_DH']
        self.elec_demand = dem['elec_demand']
        self.heat_demand = dem['heat_demand']

        self.return_temp = dem['return_temp_DH']
        self.source_delta_t = dem['source_delta_t']

        self.myGrid = classes['myGrid']
        self.import_cost = self.myGrid.import_cost_series()
        self.export_cost = self.myGrid.export

    def pre_calculation(self, first_hour, total_timesteps):

        first_hour = first_hour
        total_timesteps = total_timesteps + self.horizon
        horizon = self.horizon

        # calculate renewable generation
        wind_user = self.myUserWindturbine.user_power()['wind_user']
        wind_data = (
            self.myDatabaseWindturbine.database_power()['wind_database'])
        wind = wind_user + wind_data
        PV = self.myPV.power_output()

        RES = wind_user + wind_data + PV

        # heat pump performance over the year
        hp_performance = self.myHeatPump.performance()

        # thermal storage max capacity in each timestep
        max_capacity = np.zeros(total_timesteps)

        # temp parameters
        rt = self.return_temp
        st = self.source_temp
        ft = self.flow_temp

        final_hour = first_hour + total_timesteps
        if final_hour >= 8759 - horizon:
            final_hour = 8759

        for timestep in range(first_hour, final_hour):
            t = timestep - first_hour
            return_temp_nodes = []
            for n in range(self.myHotWaterTank.number_nodes):
                return_temp_nodes.append(rt)
            # charging from return temp to source temp is max capacity
            max_capacity[t] = self.myHotWaterTank.max_energy_in_out(
                'charging', return_temp_nodes,
                st[timestep], ft[timestep], rt, timestep)

        # create instance of Check class
        myCheck = tools.CheckFunctions(
            RES, self.elec_demand, self.heat_demand)
        # the electricity match metrics are performed over the entire year
        elec_match = myCheck.electrical_surplus_deficit()
        match = elec_match['match']
        surplus = elec_match['surplus']
        deficit = elec_match['deficit']
        # RES_used_demand = elec_match['RES_used']

        # temp parameters
        # rt = self.return_temp
        # st = self.source_temp
        # ft = self.flow_temp

        # heat_pump_renewable_demand = np.zeros(total_timesteps)
        # heat_pump_renewable_usage = np.zeros(total_timesteps)
        # _RES_used = np.zeros(total_timesteps)
        # hp_left = np.zeros(total_timesteps)
        # max_capacity = np.zeros(total_timesteps)

        # final_hour = first_hour + total_timesteps
        # if final_hour >= 8759 - horizon:
        #     final_hour = 8759

        # for timestep in range(first_hour, final_hour):

        #         t = timestep - first_hour
        #         # USE HEAT PUMP WITH SURPLUS TO MEET HEAT DEMAND
        #         # hpr - heat pump renewable
        #         hpr = self.myHeatPump.thermal_output(
        #             surplus[timestep], hp_performance[timestep],
        #             self.heat_demand[timestep])
        #         # thermal output from heat pump running on renewables
        #         heat_pump_renewable_demand[t] = hpr['hp_demand']
        #         # electrical usage of RES by heat pump running on renewables
        #         heat_pump_renewable_usage[t] = hpr['hp_elec']
        #         _RES_used[t] = (
        #             surplus[timestep] - heat_pump_renewable_usage[t])
        #         # STILL RES SURPLUS?

        #         # calculates the RES used so far
        #         # only the heat pump so far
        #         RES_used1 = heat_pump_renewable_usage[t]
        #         # checks if there is a surplus
        #         surplus_check = myCheck.surplus_check(
        #             surplus[timestep], RES_used1)
        #         # if there is surplus
        #         if surplus_check is True:
        #             # CHARGE THERMAL STORAGE WITH HEAT PUMP DRIVEN BY SURPLUS

        #             # calculate the RES leftover
        #             RES_left1 = surplus[timestep] - RES_used1
        #             duty = hp_performance[timestep]['duty']
        #             # capacity of heat pump leftover
        #             hp_cap_left = duty - heat_pump_renewable_demand[t]
        #             # max heat from heat pump running surplus
        #             hp_max_RES = hp_performance[timestep]['cop'] * RES_left1
        #             hp_left[t] = min(hp_cap_left, hp_max_RES)
        #             if self.myHeatPump.capacity == 0:
        #                 hp_left[t] = 0

        #         return_temp_nodes = []
        #         for n in range(self.myHotWaterTank.number_nodes):
        #             return_temp_nodes.append(rt)
        #         # charging from return temp to source temp is max capacity
        #         max_capacity[t] = self.myHotWaterTank.max_energy_in_out(
        #             'charging', return_temp_nodes,
        #             st[timestep], ft[timestep], rt, timestep)

        pre_calc = {
            'hp_performance': hp_performance,
            # 'heat_pump_renewable_demand': heat_pump_renewable_demand,
            # 'hp_left': hp_left,
            # '_RES_used': _RES_used,
            'max_capacity': max_capacity,
            'surplus': surplus,
            'deficit': deficit,
            'match': match,
            'generation_total': RES,
            'wind': wind,
            'PV': PV}
            # 'RES_used_demand': RES_used_demand}

        return pre_calc

    def solve(self, pre_calc, hour, first_hour, final_hour, prev_result):

        # over the whole year
        hp_performance = pre_calc['hp_performance']
        surplus = pre_calc['surplus']
        deficit = pre_calc['deficit']
        match = pre_calc['match']
        generation_total = pre_calc['generation_total']
        wind = pre_calc['wind']
        PV = pre_calc['PV']

        # over the first hour to final hour plus horizon
        # indexed from 0 to final hour plus horizon
        max_capacity = pre_calc['max_capacity']

        # temp parameters
        rt = self.return_temp
        st = self.source_temp
        ft = self.flow_temp
        sdt = self.source_delta_t

        number_timesteps = final_hour - hour
        t1 = hour - first_hour
        t2 = final_hour - first_hour

        m = GEKKO(remote=False)
        m.time = np.linspace(
            0, number_timesteps - 1, number_timesteps)

        # cost coefficient... import cost
        IC = m.Param(
            value=list(self.import_cost[hour:final_hour]))

        # elec demand and res used for elec demand
        # renewable used
        RES = m.Param(value=list(generation_total[hour:final_hour]))
        RES_ed = m.Var(value=prev_result['RES_ed'], lb=0)
        # elec demand
        ed = m.Param(value=list(self.elec_demand[hour:final_hour].values))
        # surplus = m.Param(value=surplus[hour:final_hour].values)
        export = m.Var(value=prev_result['export'], lb=0)
        # import straight to electrical demand
        imp_ed = m.Var(value=prev_result['imp_ed'], lb=0)

        # heat demand
        hd = m.Param(value=list(self.heat_demand[hour:final_hour].values))

        # heat pump output from renewables
        # heat pump renewable thermal output to demand
        HPtrd = m.Var(value=prev_result['HPtrd'], lb=0)
        # heat pump renewable to storage
        # maximum charging to storage with renewables
        HPtrs = m.Var(value=prev_result['HPtrs'], lb=0)
        # heat pump output from imports to demand
        HPtid = m.Var(value=prev_result['HPtid'], lb=0)
        # heat pump output from imports to storage
        HPtis = m.Var(value=prev_result['HPtis'], lb=0)
        # heat pump output from ES to demand
        HPtesd = m.Var(value=prev_result['HPtis'], lb=0)
        # performance of heat pump parameters
        cop = []
        duty = []
        HP_min = []
        for i in range(hour, final_hour):
            if self.myHeatPump == 0:
                duty.append(0.0)
            else:
                duty.append(hp_performance[i]['duty'])
            cop.append(hp_performance[i]['cop'])
            HP_min.append(
                hp_performance[i]['duty'] *
                self.myHeatPump.minimum_output *
                self.myHeatPump.minimum_runtime / 60 /
                100.0)
        cop = m.Param(value=cop)
        duty = m.Param(value=duty)
        HP_min = m.Param(value=HP_min)
        # heat pump on/off status
        HP_status = m.Var(
            value=prev_result['HP_status'], lb=0, ub=1, integer=True)
        # heat pump output without on/off status
        HPt_var = m.Var(value=prev_result['HPt_var'], lb=0)
        # heat pump total output
        HPt = m.Intermediate(HP_status * HPt_var)

        # thermal storage parameters
        # max capacity
        max_cap = m.Param(value=list(max_capacity[t1:t2]))
        # initial state of charge
        init_soc = self.myHotWaterTank.max_energy_in_out(
            'discharging', prev_result['final_nodes_temp'],
            st[hour], ft[hour], rt, hour)
        # max_charge = m.Intermediate(max_cap - init_soc)
        # for clarity max discharge is simply the soc
        # storage charge/discharge
        TSc = m.Var(value=prev_result['TSc'], lb=0)
        TSd = m.Var(value=prev_result['TSd'], lb=0)
        # soc = m.Intermediate(init_soc + TSc - TSd)
        soc = m.Var(value=init_soc, lb=0)
        max_charge = m.Intermediate(max_cap - soc)
        loss = m.Intermediate(0.01 * soc)
        # loss = m.Intermediate(0.0)

        # electrical storage parameters
        # max capacity
        max_cap_ES = m.Const(self.myElectricalStorage.capacity)
        # print(max_cap_ES.value)
        # print(prev_result['soc_ES'])
        max_charge_ES = m.Const(self.myElectricalStorage.charge_max)
        max_discharge_ES = m.Const(self.myElectricalStorage.discharge_max)
        charge_eff = m.Const(self.myElectricalStorage.charge_eff)
        discharge_eff = m.Const(self.myElectricalStorage.discharge_eff)
        # for clarity max discharge is simply the soc
        # storage charge/discharge
        ESc = m.Var(value=prev_result['ESc'], lb=0)
        ESc_res = m.Var(value=prev_result['ESc_res'], lb=0)
        ESc_imp = m.Var(value=prev_result['ESc_imp'], lb=0)
        ESd = m.Var(value=prev_result['ESd'], lb=0)
        ESd_hp = m.Var(value=prev_result['ESd_hp'], lb=0)
        ESd_aux = m.Var(value=prev_result['ESd_aux'], lb=0)
        ESd_ed = m.Var(value=prev_result['ESd_ed'], lb=0)
        soc_ES = m.Var(value=prev_result['soc_ES'], lb=0)
        loss_ES = m.Intermediate(self.myElectricalStorage.self_discharge * soc_ES)

        # aux parameters
        # back-up electrical heater
        # capacity is equal to peak demand
        aux_cap = np.amax(self.heat_demand.values)
        # aux from renewables to demand
        # only electric aux
        aux_rd = m.Var(value=prev_result['aux_rd'], lb=0)
        # only electric aux
        # aux from from renewables to storage
        aux_rs = m.Var(value=prev_result['aux_rs'], lb=0)
        # aux for demand
        aux_d = m.Var(value=prev_result['aux_d'], lb=0)
        # aux for storage
        aux_s = m.Var(value=prev_result['aux_s'], lb=0)
        # aux_cap = 1000
        aux = m.Var(value=prev_result['aux'], lb=0)

        if self.myAux.fuel == 'Electric':
            aux_cost = m.Param(
                value=list(self.import_cost[hour:final_hour]))
        else:
            aux_cost = m.Const(self.myAux.cost)

        # equations

        # different for electric since it can use RES production
        if self.myAux.fuel == 'Electric':
            # equalities
            m.Equations(
                [soc_ES.dt() == ESc * charge_eff - ESd - loss_ES,
                 ESd == ESd_ed + ESd_hp + ESd_aux,
                 ESc == ESc_res + ESc_imp,
                 ed == RES_ed + imp_ed + ESd_ed * discharge_eff,
                 hd == HPtrd + HPtid + HPtesd + aux_d + aux_rd + ESd_aux * discharge_eff + TSd,
                 soc.dt() == TSc - TSd - loss,
                 HPtesd == ESd_hp * cop * discharge_eff,
                 HP_status * HPt_var == HPtrs + HPtrd + HPtid + HPtis + HPtesd,
                 aux == aux_d + aux_s + aux_rd + aux_rs + ESd_aux,
                 TSc == HPtrs + HPtis + aux_rs + aux_s,
                 RES == RES_ed + (HPtrs + HPtrd) / cop + ESc_res + aux_rd + aux_rs + export
                 ])
        # other auxiliary sources can't use the RES
        else:
            # equalities
            m.Equations(
                # heat demand must be met,
                # but can be exceeded if needed to store more
                [soc_ES.dt() == ESc * charge_eff - ESd - loss_ES,
                 ESd == ESd_ed,
                 ESc == ESc_res + ESc_imp,
                 ed == RES_ed + imp_ed + ESd_ed * discharge_eff,
                 hd == HPtrd + HPtid + aux_d + TSd,
                 soc.dt() == TSc - TSd - loss,
                 HP_status * HPt_var == HPtrs + HPtrd + HPtid + HPtis,
                 aux == aux_d + aux_s,
                 TSc == HPtrs + HPtis + aux_s,
                 RES == RES_ed + (HPtrs + HPtrd) / cop + ESc_res + export
                 ])

        # inequalities
        m.Equations(
            [HPt_var <= duty,
             HPt_var >= HP_min,
             soc <= max_cap,
             TSc <= max_charge,
             TSd <= soc,
             soc_ES <= max_cap_ES,
             ESc <= max_charge_ES * charge_eff,
             ESd <= max_discharge_ES,
             ESd <= soc_ES,
             aux <= aux_cap])

        # self.export_cost = 1
        # objective
        # last term is to disadvantage charging e store with res
        m.Obj(IC / 1000 *
              ((HPt - HPtrd - HPtesd - HPtrs) / cop +
               imp_ed + ESc_imp) +
              (aux - aux_rs - aux_rd - ESd_aux) * aux_cost / 1000 -
              export * self.export_cost / 1000 + 0.00001 * ESc_res)

        m.options.IMODE = 6  # MPC mode
        m.options.SOLVER = 1  # APOPT for solving MINLP problems
        if self.myHeatPump.minimum_output == 0:
            i = 'minlp_as_nlp 1'
        else:
            i = 'minlp_as_nlp 0'
        m.solver_options = ['minlp_maximum_iterations 500', \
                            # minlp iterations with integer solution
                            'minlp_max_iter_with_int_sol 500', \
                            # treat minlp as nlp
                            'minlp_as_nlp 1', \
                            # nlp sub-problem max iterations
                            'nlp_maximum_iterations 500', \
                            # 1 = depth first, 2 = breadth first
                            'minlp_branch_method 1', \
                            # maximum deviation from whole number
                            'minlp_integer_tol 0.05', \
                            # covergence tolerance
                            'minlp_gap_tol 0.05']

        m.solve(disp=False)

        # print hour
        # print HP_status[1], 'status'
        # print HP_min[1], 'min'
        # print HPt[1], 'HPt'
        # print HPtrs[1], 'HPtrs'
        # print HPtrd[1], 'HPtrd'
        # print HPtis[1], 'HPtis'
        # print HPtid[1], 'HPtid'
        # print aux[1], 'aux'
        # print aux_rs[1], 'aux res store'
        # print aux_rd[1], 'aux res dem'
        # print aux_d[1], 'aux_d'
        # print aux_s[1], 'aux_s'
        # print TSc[1], 'TSc'
        # print max_charge[1], 'max_charge'
        # print TSd[1], 'TSd'
        # print soc[1], 'soc'
        # print hd[1], 'hd'
        # print IC[1], 'import_price'

        h = 1

        TSc_ = round(TSc[h] - TSd[h], 2)
        TSd_ = round(TSd[h] - TSc[h], 2)

        if TSc_ > TSd_:
            max_c = self.myHotWaterTank.max_energy_in_out(
                'charging',
                prev_result['final_nodes_temp'],
                st[h], ft[h], rt, h)
            TSc[h] = min(max_c, TSc_)
            TSd[h] = 0
            if TSc[h] == 0.0:
                state = 'standby'
            else:
                state = 'charging'
        elif TSd_ > TSc_:
            max_d = self.myHotWaterTank.max_energy_in_out(
                'discharging',
                prev_result['final_nodes_temp'],
                st[h], ft[h], rt, h)
            TSd[h] = min(max_d, TSd_)
            TSc[h] = 0.0
            if TSd[h] == 0.0:
                state = 'standby'
            else:
                state = 'discharging'
        else:
            state = 'standby'

        # thermal_output = HPt[h] + aux[h]
        # next_nodes_temp = self.myHotWaterTank.new_nodes_temp(
        #     state, prev_result['final_nodes_temp'], st[h], sdt, ft[h],
        #     rt, thermal_output, hd[h], hour + h)
        if self.myHotWaterTank.capacity == 0:
            final_nodes_temp = prev_result['final_nodes_temp']
        else:
            if self.myAux.fuel == 'Electric':
                # thermal_output = HPt[h] + aux[h]
                next_nodes_temp = self.myHotWaterTank.new_nodes_temp(
                    state, prev_result['final_nodes_temp'], st[h], sdt, ft[h],
                    rt, TSc[h], TSd[h], hour + h)
                final_nodes_temp = next_nodes_temp[-1]

        # final_nodes_temp = [round(elem, 2) for elem in final_nodes_temp]
        # print prev_result['final_nodes_temp'], 'prev_result'
        # print final_nodes_temp

        # results are for the second timestep
        timestep = hour + 1
        results = self.set_of_results()

        # elec demand results
        results['elec_demand']['elec_demand'] = self.elec_demand[timestep]
        results['elec_demand']['RES'] = RES_ed[h]
        results['elec_demand']['import'] = imp_ed[h]
        results['elec_demand']['ES'] = (
            ESd_ed[h] * self.myElectricalStorage.discharge_eff)

        # RES results
        results['RES']['generation_total'] = generation_total[timestep]
        results['RES']['wind'] = wind[timestep]
        results['RES']['PV'] = PV[timestep]
        results['RES']['elec_demand'] = RES_ed[h]
        results['RES']['HP'] = (
            (HPtrd[h] + HPtrs[h]) /
            hp_performance[timestep]['cop'])
        # print results['RES']['HP']
        if self.myAux.fuel == 'Electric':
            results['RES']['aux'] = aux_rd[h] + aux_rs[h]
        results['RES']['export'] = export[h]

        # heat pump results
        results['HP']['cop'] = hp_performance[timestep]['cop']
        results['HP']['duty'] = hp_performance[timestep]['duty']
        results['HP']['heat_total_output'] = HPt[h]
        results['HP']['heat_from_ES_to_demand'] = HPtesd[h]
        results['HP']['heat_to_heat_demand'] = min(
            results['HP']['heat_total_output'],
            hd[h])
        results['HP']['heat_to_TS'] = (
            results['HP']['heat_total_output'] -
            results['HP']['heat_to_heat_demand'])

        results['HP']['elec_total_usage'] = (
            results['HP']['heat_total_output'] /
            results['HP']['cop'])
        results['HP']['elec_RES_usage'] = (
            results['RES']['HP'])
        results['HP']['elec_from_ES_to_demand'] = (
            results['HP']['heat_from_ES_to_demand'] /
            results['HP']['cop'])
        results['HP']['elec_import_usage'] = (
            results['HP']['elec_total_usage'] -
            results['HP']['elec_RES_usage'] -
            results['HP']['elec_from_ES_to_demand'])

        # heat demand results
        results['heat_demand']['TS'] = TSd[h]
        results['heat_demand']['heat_demand'] = self.heat_demand[timestep]
        results['heat_demand']['HP'] = results['HP']['heat_to_heat_demand']
        results['heat_demand']['aux'] = aux[h]

        # TS results
        results['TS']['charging_total'] = TSc[h]
        results['TS']['discharging_total'] = TSd[h]
        results['TS']['HP_to_TS'] = (
            results['HP']['heat_to_TS'])
        results['TS']['HP_from_RES_to_TS'] = (
            results['HP']['heat_from_RES_to_TS'])
        results['TS']['HP_from_import_to_TS'] = (
            results['HP']['heat_from_import_to_TS'])
        results['TS']['aux_to_TS'] = (
            results['TS']['charging_total'] -
            results['TS']['HP_to_TS'])
        results['TS']['final_nodes_temp'] = final_nodes_temp

        # # ES results
        results['ES']['charging_from_RES'] = ESc_res[h]
        results['ES']['charging_from_import'] = ESc_imp[h]
        results['ES']['charging_total'] = (
            results['ES']['charging_from_RES'] +
            results['ES']['charging_from_import'])
        results['ES']['discharging_to_demand'] = (
            ESd_ed[h] * self.myElectricalStorage.discharge_eff)
        results['ES']['discharging_to_HP'] = ESd_hp[h]
        results['ES']['discharging_to_aux'] = ESd_aux[h]
        results['ES']['discharging_total'] = (
            results['ES']['discharging_to_demand'] +
            results['ES']['discharging_to_HP'] +
            results['ES']['discharging_to_aux'])
        # update state of charge
        # new soc
        final_soc = soc_ES[h]
        results['ES']['final_soc'] = final_soc

        # AUX results
        results['aux']['demand'] = aux[h]
        results['aux']['usage'] = self.myAux.fuel_usage(
            results['aux']['demand'])
        if self.myAux.fuel == 'Electric':
            aux_price = results['grid']['import_price'] / 1000.
            density = 0.0
        else:
            aux_price = self.myAux.cost / 1000.
            density = self.myAux.energy_density
        results['aux']['cost'] = aux_price * results['aux']['demand']
        results['aux']['mass'] = density * results['aux']['usage']

        # grid results
        results['grid']['import_for_elec_demand'] = (
            results['elec_demand']['import'])
        results['grid']['import_for_heat_pump_total'] = (
            results['HP']['elec_import_usage'])
        results['grid']['import_for_ES'] = (
            results['ES']['charging_from_import'])
        results['grid']['total_export'] = results['RES']['export']
        if self.myAux.fuel == 'Electric':
            results['grid']['total_import'] = (
                results['grid']['import_for_elec_demand'] +
                results['grid']['import_for_heat_pump_total'] +
                results['grid']['import_for_ES'] +
                results['aux']['demand'] -
                results['RES']['aux'])
        else:
            results['grid']['total_import'] = (
                results['grid']['import_for_elec_demand'] +
                results['grid']['import_for_heat_pump_total'] +
                results['grid']['import_for_ES'])

        results['grid']['import_price'] = IC[h]
        # this is in pounds
        # divide by 1000 because import price in pound/MWh
        # total import is in kWH
        results['grid']['import_costs'] = (
            results['grid']['total_import'] *
            results['grid']['import_price'] / 1000.)
        results['grid']['export_income'] = (
            results['grid']['total_export'] *
            self.export_cost / 1000.)
        results['grid']['cashflow'] = (
            results['grid']['export_income'] -
            results['grid']['import_costs'])
        results['grid']['surplus'] = surplus[timestep]
        results['grid']['deficit'] = deficit[timestep]
        results['grid']['match'] = match[timestep]

        next_results = {
            'HPt': HPt[h], 'HPtrs': HPtrs[h],
            'HPtrd': HPtrd[h], 'HPtid': HPtid[h],
            'HPtis': HPtis[h], 'HPtesd': HPtesd[h], 'HP_status': HP_status[h],
            'HPt_var': HPt_var[h], 'aux': aux[h],
            'aux_rd': aux_rd[h], 'aux_rs': aux_rs[h],
            'aux_d': aux_d[h], 'aux_s': aux_s[h],
            'TSc': TSc[h], 'TSd': TSd[h],
            'final_nodes_temp': final_nodes_temp, 'state': state,
            'import_cost': IC[h], 'export': export[h],
            'soc_ES': soc_ES[h],
            'ESc': ESc[h], 'ESc_imp': ESc_imp[h], 'ESc_res': ESc_res[h],
            'ESd': ESd[h], 'ESd_ed': ESd_ed[h], 'ESd_hp': ESd_hp[h],
            'ESd_aux': ESd_aux[h],
            'imp_ed': imp_ed[h], 'RES_ed': RES_ed[h]}

        # print results

        # print hd.value, 'hd'
        # print HPt.value, 'HPt'
        # print duty.value, 'duty'
        # print cop.value, 'cop'
        # print aux.value, 'aux'
        # print TSc.value, 'charging'
        # print TSd.value, 'discharging'
        # print soc.value, 'soc'
        # print IC.value, 'import cost'
        # print aux_cost.value, 'auxiliary cost'
        # print HPtrd.value, 'heat pump renewable to demand'
        # print HPtrs.value, 'heat pump renewable to storage'
        # print cop.value, 'cop'
        # print max_charge.value, 'max charge'
        # print final_nodes_temp, 'final_nodes_temp'
        # print HPtrs.value, 'HPtrs'
        # print HP_left.value, 'heat pump capacity left'
        # print max_charge.value, 'max charge available'
        # print HPtrd.value, 'HPtrd'
        # print HPtrd_max.value, 'HPtrd_max'
        # print surplus[first_hour:final_hour].values, 'surplus'
        # print cop.value, 'cop'
        # print duty.value, 'duty'

        # Plot solution
        # plt.figure()
        # plt.subplot(4, 1, 1)
        # plt.plot(m.time, HPt.value, 'r', LineWidth=2)
        # plt.plot(m.time, aux.value, 'y', LineWidth=2)
        # plt.plot(m.time, hd.value, 'g', LineWidth=2)
        # plt.ylabel(['HPt', 'aux', 'HD'])
        # plt.legend(['HPt', 'aux', 'HD'], loc='best')
        # plt.subplot(4, 1, 2)
        # plt.plot(m.time, soc.value, 'b', LineWidth=2)
        # plt.legend(['SOC'], loc='best')
        # plt.ylabel('SOC')
        # plt.subplot(4, 1, 3)
        # plt.plot(m.time, IC.value, 'g', LineWidth=2)
        # plt.legend(['Import cost'], loc='best')
        # plt.ylabel('Import cost')
        # plt.subplot(4, 1, 4)
        # plt.plot(m.time, surplus.value, 'm', LineWidth=2)
        # plt.legend([r'surplus'], loc='best')
        # plt.ylabel('Surplus')
        # plt.xlabel('Time')
        # plt.show()
        return {'results': results, 'next_results': next_results}

    def moving_horizon(self, pre_calc, first_hour, timesteps):

        horizon = self.horizon
        final_hour = first_hour + timesteps

        # includes a progress bar, purely for aesthetics
        widgets = ['Running: ' + self.subname, ' ', Percentage(), ' ',
                   Bar(marker=RotatingMarker(), left='[', right=']'),
                   ' ', ETA()]
        pbar = ProgressBar(widgets=widgets, maxval=timesteps)
        pbar.start()

        if final_hour > 8760:
            raise Exception('Timesteps extend beyond end of year...')

        results = []
        next_results = []
        for hour in range(first_hour, final_hour - 1):
            final_horizon_hour = hour + horizon
            if final_horizon_hour > 8759:
                final_horizon_hour = 8759

            if hour == first_hour or hour == 8758:

                # if very first result then previous results are zero
                hp_performance = pre_calc['hp_performance']
                duty = hp_performance[first_hour]['duty']
                # max_charge = pre_calc['max_capacity'][0]
                hd = self.heat_demand[first_hour]
                if duty >= hd:
                    # TSc = min(leftover, max_charge)
                    HPt = hd
                    aux = 0
                    # leftover = duty - hd
                    # TSc = min(leftover, max_charge)
                    # HPt = hd + TSc
                    # aux = 0
                elif duty < hd:
                    HPt = duty
                    aux = hd - duty

                init_temps = self.myHotWaterTank.init_temps(
                    self.return_temp)
                ES_init = self.myElectricalStorage.init_state()
                # final_nodes_temp = self.myHotWaterTank.new_nodes_temp(
                #     state, init_temps, self.source_temp[first_hour],
                #     self.source_delta_t, self.flow_temp[first_hour],
                #     self.return_temp, HPt,
                #     self.heat_demand[first_hour], first_hour)[
                #         self.myHotWaterTank.number_nodes - 1]
                prev_result = {
                    'HPt': 0, 'HPtrs': 0,
                    'HPtrd': 0, 'HPtid': 0,
                    'HPtis': 0, 'HPtesd': 0., 'HP_status': 0,
                    'HPt_var': 0, 'aux': 0,
                    'aux_rd': 0, 'aux_rs': 0,
                    'aux_d': 0, 'aux_s': 0,
                    'TSc': 0, 'TSd': 0,
                    'final_nodes_temp': init_temps, 'state': 'standby',
                    'import_cost': self.import_cost[first_hour],
                    'export': self.export_cost,
                    'soc_ES': ES_init,
                    'ESc': 0., 'ESc_imp': 0., 'ESc_res': 0.,
                    'ESd': 0., 'ESd_ed': 0., 'ESd_hp': 0.,
                    'ESd_aux': 0.,
                    'imp_ed': 0., 'RES_ed': 0.}
                res = self.set_of_results()
                res['TS']['final_nodes_temp'] = init_temps
                res['ES']['final_soc'] = ES_init
                res['HP']['heat_total_output'] = HPt
                res['aux']['demand'] = aux
                res['grid']['import_price'] = self.import_cost[first_hour]
                res['heat_demand']['heat_demand'] = (
                    self.heat_demand[first_hour])
                res['HP']['cop'] = hp_performance[first_hour]['cop']
                res['HP']['duty'] = hp_performance[first_hour]['duty']
                results.append(res)
                next_results.append(prev_result)

                if hour == first_hour:
                    r = self.solve(
                        pre_calc, hour, first_hour, final_horizon_hour,
                        prev_result)
                    results.append(r['results'])
                    next_results.append(r['next_results'])

            else:
                try:
                    prev_result = next_results[hour - first_hour]
                    r = self.solve(
                        pre_calc, hour, first_hour, final_horizon_hour,
                        prev_result)
                    results.append(r['results'])
                    next_results.append(r['next_results'])
                except:
                    # prev_result = next_results[hour - first_hour - 1]
                    # r = self.solve(
                    #     pre_calc, hour, first_hour, final_horizon_hour,
                    #     prev_result)
                    # results.append(r['results'])
                    # next_results.append(r['next_results'])
                # finally:
                    prev_result = {
                        'HPt': 0, 'HPtrs': 0,
                        'HPtrd': 0, 'HPtid': 0,
                        'HPtis': 0, 'HPtesd': 0, 'HP_status': 0,
                        'HPt_var': 0, 'aux': 0,
                        'aux_rd': 0, 'aux_rs': 0,
                        'aux_d': 0, 'aux_s': 0,
                        'TSc': 0, 'TSd': 0,
                        'final_nodes_temp': init_temps, 'state': 'standby',
                        'import_cost': self.import_cost[first_hour],
                        'export': self.export_cost,
                        'soc_ES': ES_init,
                        'ESc': 0., 'ESc_imp': 0., 'ESc_res': 0.,
                        'ESd': 0., 'ESd_ed': 0., 'ESd_hp': 0.,
                        'ESd_aux': 0.,
                        'imp_ed': 0., 'RES_ed': 0.}
                    r = self.solve(
                        pre_calc, hour, first_hour, final_horizon_hour,
                        prev_result)
                    results.append(r['results'])
                    next_results.append(r['next_results'])

            # update for progress bar
            pbar.update(hour - first_hour + 1)
        # stop progress bar
        pbar.finish()

        # HPt = []
        # aux = []
        # final_nodes_temp = []
        # TSc = []
        # TSd = []
        # state = []
        # IC = []
        # for i in range(timesteps):
        #     HPt.append(results[i]['HPt'])
        #     aux.append(results[i]['aux'])
        #     final_nodes_temp.append(results[i]['final_nodes_temp'])
        #     TSc.append(results[i]['TSc'])
        #     TSd.append(results[i]['TSd'])
        #     IC.append(results[i]['import_cost'])
        #     if results[i]['state'] == 'charging':
        #         state.append(1)
        #     elif results[i]['state'] == 'discharging':
        #         state.append(-1)
        #     else:
        #         state.append(0)

        # surplus = pre_calc['surplus']
        # print timesteps, 'timesteps'
        # print first_hour, 'first'
        # print final_hour, 'last'
        # hd = self.heat_demand[first_hour:final_hour]

        # print TSc, 'TSc'
        # print TSd, 'TSd'
        # print hd.values, 'hd'
        # print HPt, 'HPt'
        # print aux, 'aux'

        # HPt = []
        # cop = []
        # aux = []
        # final_nodes_temp = []
        # TSc = []
        # TSd = []
        # IC = []
        # surplus = []
        # hd = []
        # export = []
        # for i in range(timesteps):
        #     HPt.append(results[i]['HP']['heat_total_output'])
        #     cop.append(results[i]['HP']['cop'])
        #     aux.append(results[i]['aux']['demand'])
        #     final_nodes_temp.append(results[i]['TS']['final_nodes_temp'])
        #     TSc.append(results[i]['TS']['charging_total'])
        #     TSd.append(results[i]['TS']['discharging_total'])
        #     IC.append(results[i]['grid']['import_price'])
        #     surplus.append(results[i]['grid']['surplus'])
        #     hd.append(results[i]['heat_demand']['heat_demand'])
        #     export.append(results[i]['grid']['total_export'])

        # # # Plot solution
        # time = range(first_hour, final_hour)
        # plt.figure()
        # plt.subplot(4, 1, 1)
        # plt.plot(time, HPt, 'r', LineWidth=2)
        # plt.plot(time, aux, 'y', LineWidth=2)
        # plt.plot(time, hd, 'g', LineWidth=2)
        # plt.ylabel('HPt, aux and HD')
        # plt.legend(['HPt', 'aux', 'HD'], loc='best')
        # plt.subplot(4, 1, 2)
        # plt.plot(time, final_nodes_temp, 'b', LineWidth=2)
        # plt.legend(['Node temperature'], loc='best')
        # plt.ylabel('Node temperature')
        # plt.subplot(4, 1, 3)
        # plt.plot(time, IC, 'g', LineWidth=2)
        # plt.legend(['Import cost'], loc='best')
        # plt.ylabel('Import cost')
        # plt.subplot(4, 1, 4)
        # # plt.plot(time, cop, 'm', LineWidth=2)
        # # plt.legend(['cop'], loc='best')
        # # plt.ylabel('cop')
        # plt.plot(time, surplus, 'm', LineWidth=2)
        # plt.plot(time, export, 'b', LineWidth=2)
        # plt.legend(['surplus', 'export'], loc='best')
        # plt.ylabel('Surplus, and export')
        # # plt.plot(time, TSc, 'r', LineWidth=2)
        # # plt.plot(time, TSd, 'g', LineWidth=2)
        # # plt.legend(['TSc', 'TSd'], loc='best')
        # # plt.ylabel('Charging/discharging')
        # plt.xlabel('Time')
        # plt.show()

        # write the outputs to a pickle
        file = os.path.join(
            os.path.dirname(__file__), '..', 'outputs',
            self.name[:-5], self.subname, 'outputs.pkl')
        with open(file, 'wb') as output_file:
            pickle.dump(results, output_file,
                        protocol=pickle.HIGHEST_PROTOCOL)

        return results

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
               'cost': 0.0  #
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
