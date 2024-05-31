import logging
import pandas as pd
from pathlib import Path
import numpy as np
import shutil
import pickle
# import register_matplotlib_converters
import matplotlib
import matplotlib.pyplot as plt
from tqdm import tqdm
from typing import Dict

from . import inputs
from .. import tools as t
from ..constants import INDIR, OUTDIR
from ..power import grid

LOG = logging.getLogger(__name__)

"""
plt.style.available

['seaborn-bright',
'seaborn-darkgrid',
'seaborn-white',
'ggplot',
'seaborn-dark',
'seaborn-muted',
'seaborn-notebook',
'seaborn-paper',
'classic',
'grayscale',
'seaborn-whitegrid',
'fivethirtyeight',
'bmh',
'seaborn-ticks',
'seaborn-dark-palette',
'seaborn-pastel',
'dark_background',
'seaborn-deep',
'seaborn-colorblind',
'seaborn-talk',
'seaborn-poster']
"""
# register_matplotlib_converters()
# plt.style.use('seaborn-paper')

# Use non interactive backend to avoid windows popping up
matplotlib.use('Agg')
plt.style.use(['ggplot', 'fast'])
plt.rcParams.update({'font.size': 6})

FIG_DPI = 200


def run_plots(root: str | Path, subname: str):
    root = Path(root).resolve()
    myInputs = inputs.Inputs(root, subname)
    # controller inputs
    controller_info = myInputs.controller()['controller_info']
    timesteps = controller_info['total_timesteps']

    jobs = []

    if timesteps == 8760:
        for period in ['Year', 'Winter', 'Summer']:
            myPlots = Plot(root, subname, period)
            jobs.append(myPlots.operation)
            jobs.append(myPlots.elec_demand_and_RES)
            jobs.append(myPlots.HP_and_heat_demand)
            jobs.append(myPlots.TS)
            jobs.append(myPlots.ES)
            jobs.append(myPlots.grid)
            if period == 'Year':
                jobs.append(myPlots.RES_bar)
    else:
        period = 'User'
        myPlots = Plot(root, subname, period)
        jobs.append(myPlots.operation)
        jobs.append(myPlots.elec_demand_and_RES)
        jobs.append(myPlots.HP_and_heat_demand)
        jobs.append(myPlots.TS)
        jobs.append(myPlots.ES)
        jobs.append(myPlots.grid)
        jobs.append(myPlots.RES_bar)

    for job in tqdm(jobs, desc=f"Plotting: {subname}"):
        job()

def run_KPIs(root: str | Path):
    root = Path(root).resolve()

    jobs = []

    my3DPlots = ThreeDPlots(root)
    jobs.append(my3DPlots.KPIs_to_csv)
    jobs.append(my3DPlots.plot_opex)
    jobs.append(my3DPlots.plot_RES)
    jobs.append(my3DPlots.plot_heat_from_RES)
    jobs.append(my3DPlots.plot_HP_size_ratio)
    jobs.append(my3DPlots.plot_HP_utilisation)
    jobs.append(my3DPlots.plot_capital_cost)
    jobs.append(my3DPlots.plot_LCOH)
    jobs.append(my3DPlots.plot_COH)

    for job in tqdm(jobs, desc=f"KPIs"):
        job()

class Plot(object):

    def __init__(self, root: Path, subname: str, period: str):

        self.root = Path(root).resolve()
        self.folder_path = self.root / OUTDIR / subname / period
        self.subname = subname
        # period can be 'Summer', 'Winter', 'Year', 'User'
        self.period = period

        file_output_pickle = self.root / OUTDIR / subname / 'outputs.pkl'
        self.results = pd.read_pickle(file_output_pickle)

        self.myInputs = inputs.Inputs(self.root, subname)
        # controller inputs
        controller_info = self.myInputs.controller()['controller_info']
        self.timesteps = controller_info['total_timesteps']
        self.first_hour = controller_info['first_hour']

        # creates a folder for keeping all the
        # outputs as saved from the excel file
        if self.folder_path.is_dir() is False:
            self.folder_path.mkdir()

        elif self.folder_path.is_dir() is True:
            shutil.rmtree(self.folder_path)
            self.folder_path.mkdir()

    def period_timesteps(self):

        # if it is a full year simulated
        # plot the period from class attribute
        if self.timesteps == 8760:

            if self.period == 'Summer':
                timesteps = 168
                first_hour = 4380
            elif self.period == 'Winter':
                timesteps = 168
                first_hour = 24
            elif self.period == 'Year':
                timesteps = 8760
                first_hour = 0
            elif self.period == 'User':
                timesteps = self.timesteps
                first_hour = self.first_hour
            else:
                msg = f"Period definition {self.period} is not valid, must be one of [Summer, Winter, Year, User]"
                LOG.error(msg)
                raise ValueError(msg)

        else:
            timesteps = self.timesteps
            first_hour = 0

        return {'first_hour': first_hour, 'timesteps': timesteps}

    def operation(self):

        # points to where the pdf will be saved and its name
        fileout = self.folder_path / 'operation.png'
        # pp = PdfPages(fileout)

        results = self.results
        timesteps = self.timesteps

        HPt = []
        aux = []
        final_nodes_temp = []
        IC = []
        surplus = []
        hd = []
        export = []
        for i in range(timesteps):
            HPt.append(results[i]['HP']['heat_total_output'])
            hd.append(results[i]['heat_demand']['heat_demand'])
            aux.append(results[i]['aux']['demand'])
            final_nodes_temp.append(results[i]['TS']['final_nodes_temp'])
            IC.append(results[i]['grid']['import_price'])
            surplus.append(results[i]['grid']['surplus'])
            export.append(results[i]['grid']['total_export'])

        pt = self.period_timesteps()
        first_hour = pt['first_hour']
        timesteps = pt['timesteps']
        final_hour = first_hour + timesteps

        # Plot solution
        time = range(timesteps)
        fig = plt.figure()

        plt.subplot(4, 1, 1)
        plt.title('Operation graphs')
        plt.plot(time, HPt[first_hour:final_hour], 'r', linewidth=1)
        plt.plot(time, aux[first_hour:final_hour], 'b', linewidth=1)
        plt.plot(time, hd[first_hour:final_hour], 'g', linewidth=1)
        plt.ylabel('Energy (kWh)')
        plt.legend(['HPt', 'aux', 'HD'], loc='best')

        plt.subplot(4, 1, 2)
        plt.plot(time, final_nodes_temp[first_hour:final_hour],
                 'b', linewidth=1)
        plt.ylabel('Node temperature \n (degC)')

        plt.subplot(4, 1, 3)
        plt.plot(time, IC[first_hour:final_hour], 'g', linewidth=1)
        plt.ylabel('Import cost \n (Pounds per MWh)')

        plt.subplot(4, 1, 4)
        plt.plot(time, surplus[first_hour:final_hour], 'm', linewidth=1)
        plt.plot(time, export[first_hour:final_hour], 'b', linewidth=1)
        plt.legend(['surplus', 'export'], loc='best')
        plt.ylabel('Energy (kWh)')

        plt.xlabel('Hour of the year')
        plt.tight_layout()
        
        fig.savefig(fileout, format='png', dpi=FIG_DPI, bbox_inches='tight')
        plt.close()

    def elec_demand_and_RES(self):

        # points to where the pdf will be saved and its name
        fileout = self.folder_path / 'electricity_demand_and_generation.png'
        results = self.results
        timesteps = self.timesteps
        first_hour = self.first_hour
        final_hour = first_hour + timesteps

        RES = []
        ES = []
        imp = []
        dem = []
        generation_total = []
        wind = []
        PV = []
        elec_demand = []
        HP = []
        aux = []
        export = []

        for i in range(timesteps):
            RES.append(results[i]['elec_demand']['RES'])
            ES.append(results[i]['elec_demand']['ES'])
            imp.append(results[i]['elec_demand']['import'])
            dem.append(results[i]['elec_demand']['elec_demand'])
            generation_total.append(results[i]['RES']['generation_total'])
            wind.append(results[i]['RES']['wind'])
            PV.append(results[i]['RES']['PV'])
            elec_demand.append(results[i]['RES']['elec_demand'])
            HP.append(results[i]['RES']['HP'])
            aux.append(results[i]['RES']['aux'])
            export.append(results[i]['RES']['export'])

        pt = self.period_timesteps()
        first_hour = pt['first_hour']
        timesteps = pt['timesteps']
        final_hour = first_hour + timesteps

        # Plot solution
        time = range(first_hour, final_hour)
        fig = plt.figure()

        plt.subplot(3, 1, 1)
        plt.stackplot(
            time,
            RES[first_hour:final_hour],
            imp[first_hour:final_hour],
            ES[first_hour:final_hour])
        plt.ylabel('Energy (kWh)')
        plt.legend(['RES', 'Import', 'ES'], loc='best')
        plt.title('Electrical demand')

        # Plot stack of RES generation
        plt.subplot(3, 1, 2)
        plt.stackplot(
            time,
            wind[first_hour:final_hour],
            PV[first_hour:final_hour])
        plt.ylabel('Energy (kWh)')
        plt.legend(['Wind', 'PV'], loc='best')
        plt.title('Renewable power generation')

        # Plot stack of RES usage
        plt.subplot(3, 1, 3)
        plt.stackplot(
            time,
            elec_demand[first_hour:final_hour],
            HP[first_hour:final_hour],
            aux[first_hour:final_hour],
            export[first_hour:final_hour])
        plt.ylabel('Energy (kWh)')
        plt.legend(['Elec demand', 'HP', 'Aux', 'Export'], loc='best')
        plt.title('Renewable power usage')

        plt.xlabel('Hour of the year')
        plt.tight_layout()

        fig.savefig(fileout, format='png', dpi=FIG_DPI, bbox_inches='tight')
        plt.close()

    def HP_and_heat_demand(self):

        # points to where the pdf will be saved and its name
        fileout = self.folder_path / 'heat_demand_and_heat_pump.png'

        results = self.results
        timesteps = self.timesteps
        first_hour = self.first_hour
        final_hour = first_hour + timesteps

        HP = []
        TS = []
        aux = []
        hd = []

        heat_to_heat_demand = []
        heat_to_TS = []
        heat_total_output = []

        elec_total_usage = []
        elec_RES_usage = []
        elec_ES_usage = []
        elec_import_usage = []

        cop = []
        duty = []

        for i in range(timesteps):
            HP.append(results[i]['heat_demand']['HP'])
            TS.append(results[i]['heat_demand']['TS'])
            aux.append(
                results[i]['heat_demand']['heat_demand'] -
                results[i]['heat_demand']['HP'] -
                results[i]['heat_demand']['TS'])
            hd.append(results[i]['heat_demand']['heat_demand'])
            heat_to_heat_demand.append(
                results[i]['HP']['heat_to_heat_demand'])
            heat_to_TS.append(
                results[i]['HP']['heat_to_TS'])
            heat_total_output.append(
                results[i]['HP']['heat_total_output'])
            elec_total_usage.append(
                results[i]['HP']['elec_total_usage'])
            elec_RES_usage.append(
                results[i]['HP']['elec_RES_usage'])
            elec_ES_usage.append(
                results[i]['HP']['elec_from_ES_to_demand'])
            elec_import_usage.append(
                results[i]['HP']['elec_import_usage'])
            cop.append(
                results[i]['HP']['cop'])
            duty.append(
                results[i]['HP']['duty'])

        pt = self.period_timesteps()
        first_hour = pt['first_hour']
        timesteps = pt['timesteps']
        final_hour = first_hour + timesteps

        # Plot solution
        time = range(first_hour, final_hour)
        fig = plt.figure()

        plt.subplot(3, 1, 1)
        plt.stackplot(
            time,
            HP[first_hour:final_hour],
            TS[first_hour:final_hour],
            aux[first_hour:final_hour])
        plt.ylabel('Energy (kWh)')
        plt.legend(['HP', 'TS', 'Aux'], loc='best')
        plt.title('Heat demand')

        plt.subplot(3, 1, 2)
        plt.stackplot(
            time,
            heat_to_heat_demand[first_hour:final_hour],
            heat_to_TS[first_hour:final_hour])
        plt.ylabel('Energy (kWh)')
        plt.legend(['Heat demand', 'TS'], loc='best')
        plt.title('Heat pump thermal output')

        # Plot stack of HP electricity usage
        plt.subplot(3, 1, 3)
        plt.stackplot(
            time,
            elec_RES_usage[first_hour:final_hour],
            elec_import_usage[first_hour:final_hour],
            elec_ES_usage[first_hour:final_hour])
        plt.ylabel('Energy (kWh)')
        plt.legend(['RES usage', 'Import', 'ES'], loc='best')
        plt.title('Heat pump electrical usage')

        plt.xlabel('Hour of the year')
        plt.tight_layout()

        fig.savefig(fileout, format='png', dpi=FIG_DPI, bbox_inches='tight')
        plt.close()

        fig = plt.figure()

        plt.subplot(2, 1, 1)
        plt.plot(time, cop[first_hour:final_hour], 'r', linewidth=1)
        plt.ylabel('COP')
        plt.title('Heat pump performance')

        plt.subplot(2, 1, 2)
        plt.plot(time, duty[first_hour:final_hour], 'g', linewidth=1)
        plt.ylabel('Duty (kW)')

        plt.xlabel('Hour of the year')
        plt.tight_layout()

        fileout = self.folder_path / 'heatpump_cop_and_duty.png'
        fig.savefig(fileout, format='png', dpi=FIG_DPI, bbox_inches='tight')
        plt.close()

    def TS(self):

        # points to where the pdf will be saved and its name
        fileout = self.folder_path / 'thermal_storage.png'

        results = self.results
        timesteps = self.timesteps
        first_hour = self.first_hour
        final_hour = first_hour + timesteps

        charging_total = []
        discharging_total = []
        final_nodes_temp = []

        for i in range(timesteps):
            charging_total.append(results[i]['TS']['charging_total'])
            discharging_total.append(results[i]['TS']['discharging_total'])
            final_nodes_temp.append(results[i]['TS']['final_nodes_temp'])

        pt = self.period_timesteps()
        first_hour = pt['first_hour']
        timesteps = pt['timesteps']
        final_hour = first_hour + timesteps

        # Plot solution
        time = range(first_hour, final_hour)
        fig = plt.figure()

        plt.subplot(3, 1, 1)
        plt.plot(
            time,
            charging_total[first_hour:final_hour],
            'r', linewidth=1)
        plt.ylabel('Energy (kWh)')
        plt.legend(['Charging'], loc='best')
        plt.title('Thermal storage')

        # Plot stack of RES generation
        plt.subplot(3, 1, 2)
        plt.plot(
            time,
            discharging_total[first_hour:final_hour],
            'b', linewidth=1)
        plt.ylabel('Energy (kWh)')
        plt.legend(['Discharging'], loc='best')

        # Plot stack of RES usage
        plt.subplot(3, 1, 3)
        plt.plot(
            time, final_nodes_temp[first_hour:final_hour],
            linewidth=1)
        plt.ylabel('Temperature degC')
        leg = []
        for x in range(len(final_nodes_temp[first_hour])):
            leg.append(str(x + 1))
        plt.legend(leg, loc='best')

        plt.xlabel('Hour of the year')
        plt.tight_layout()

        fig.savefig(fileout, format='png', dpi=FIG_DPI, bbox_inches='tight')
        plt.close()

    def ES(self):
        # points to where the pdf will be saved and its name
        fileout = self.folder_path / 'electrical_storage.png'

        results = self.results
        timesteps = self.timesteps
        first_hour = self.first_hour
        final_hour = first_hour + timesteps

        ES_to_demand = []
        ES_to_HP_to_demand = []
        RES_to_ES = []
        import_for_ES = []
        soc = []
        IC = []
        surplus = []
        export = []
        # dem = []

        for i in range(timesteps):
            ES_to_demand.append(-1 * results[i]['ES']['discharging_to_demand'])
            ES_to_HP_to_demand.append(-1 * results[i]['ES']['discharging_to_HP'])
            RES_to_ES.append(results[i]['ES']['charging_from_RES'])
            import_for_ES.append(results[i]['ES']['charging_from_import'])
            soc.append(results[i]['ES']['final_soc'])
            IC.append(results[i]['grid']['import_price'])
            surplus.append(results[i]['grid']['surplus'])
            export.append(results[i]['grid']['total_export'])
            # dem.append(results[i]['elec_demand']['elec_demand'])

        pt = self.period_timesteps()
        first_hour = pt['first_hour']
        timesteps = pt['timesteps']
        final_hour = first_hour + timesteps

        # Plot solution
        time = range(first_hour, final_hour)
        fig = plt.figure()
        plt.subplot(4, 1, 1)
        plt.title('Electrical Storage')
        plt.plot(time, ES_to_demand[first_hour:final_hour], 'r', linewidth=1)
        plt.plot(time, ES_to_HP_to_demand[first_hour:final_hour], 'y', linewidth=1)
        plt.plot(time, RES_to_ES[first_hour:final_hour], 'b', linewidth=1)
        plt.plot(time, import_for_ES[first_hour:final_hour], 'g', linewidth=1)
        plt.ylabel('ES c/d')
        plt.legend(['ES_to_demand', 'ES_to_HP_to_demand', 'RES_to_ES', 'import_for_ES'], loc='best')

        plt.subplot(4, 1, 2)
        plt.plot(time, soc[first_hour:final_hour], 'r', linewidth=1)
        # plt.plot(time, dem[first_hour:final_hour], 'g', linewidth=1)
        plt.ylabel('SOC')
        plt.legend(['SOC'], loc='best')

        plt.subplot(4, 1, 3)
        plt.plot(time, IC[first_hour:final_hour], 'g', linewidth=1)
        plt.ylabel('Import cost')

        plt.subplot(4, 1, 4)
        plt.plot(time, surplus[first_hour:final_hour], 'm', linewidth=1)
        plt.plot(time, export[first_hour:final_hour], 'b', linewidth=1)
        plt.legend(['surplus', 'export'], loc='best')
        plt.ylabel('Surplus, and export')

        plt.xlabel('Hour of the year')
        plt.tight_layout()

        fig.savefig(fileout, format='png', dpi=FIG_DPI, bbox_inches='tight')
        plt.close()

    def grid(self):

        # points to where the pdf will be saved and its name
        fileout = self.folder_path / 'grid.png'

        results = self.results
        timesteps = self.timesteps
        first_hour = self.first_hour
        final_hour = first_hour + timesteps

        total_export = []
        total_import = []
        import_price = []
        cashflow = []

        for i in range(timesteps):
            total_export.append(results[i]['grid']['total_export'])
            total_import.append(results[i]['grid']['total_import'])
            import_price.append(results[i]['grid']['import_price'])
            cashflow.append(results[i]['grid']['cashflow'])

        pt = self.period_timesteps()
        first_hour = pt['first_hour']
        timesteps = pt['timesteps']
        final_hour = first_hour + timesteps

        # Plot solution
        time = range(first_hour, final_hour)
        fig = plt.figure()

        plt.subplot(3, 1, 1)
        plt.title('Grid interaction')
        plt.plot(time, total_import[first_hour:final_hour], 'b', linewidth=1)
        plt.plot(time, total_export[first_hour:final_hour], 'r', linewidth=1)
        plt.ylabel('Energy (kWh)')
        plt.legend(['Import', 'Export'], loc='best')

        plt.subplot(3, 1, 2)
        plt.plot(time, import_price[first_hour:final_hour],
                 'g', linewidth=1)
        plt.ylabel('import price \n (Pounds/MWh)')

        plt.subplot(3, 1, 3)
        plt.plot(time, cashflow[first_hour:final_hour], 'y', linewidth=1)
        plt.ylabel('Cashflow \n (Pounds/MWh)')

        plt.xlabel('Hour of the year')
        plt.tight_layout()

        fig.savefig(fileout, format='png', dpi=FIG_DPI, bbox_inches='tight')
        plt.close()

    def RES_bar(self):

        # bar chart of wind
        # bar chart of pv
        # bar chart of total RES

        # points to where the pdf will be saved and its name
        fileout = self.folder_path / 'RES_bar_charts.png'

        results = self.results
        timesteps = self.timesteps

        PV = np.zeros(timesteps)
        wind = np.zeros(timesteps)
        RES = np.zeros(timesteps)

        for i in range(timesteps):
            RES[i] = results[i]['RES']['generation_total']
            wind[i] = results[i]['RES']['wind']
            PV[i] = results[i]['RES']['PV']

        wind_monthly = t.sum_monthly(wind)
        wind_year = round(wind.sum() / 1000, 2)

        PV_monthly = t.sum_monthly(PV)
        PV_year = round(PV.sum() / 1000, 2)

        RES_monthly = t.sum_monthly(RES)
        RES_year = round(RES.sum() / 1000, 2)

        # bar chart of months
        fig = plt.figure()

        plt.subplot(3, 1, 1)
        plt.bar(
            range(len(wind_monthly)),
            list(wind_monthly.values()),
            align='center')
        plt.xticks(range(len(wind_monthly)), list(wind_monthly.keys()))
        plt.yticks()
        plt.ylabel('Energy (kWh)')
        plt.title('Total Wind Production (MWh): %s' % (wind_year))

        plt.subplot(3, 1, 2)
        plt.bar(
            range(len(PV_monthly)),
            list(PV_monthly.values()),
            align='center')
        plt.xticks(range(len(PV_monthly)), list(PV_monthly.keys()))
        plt.yticks()
        plt.ylabel('Energy (kWh)')
        plt.title('Total PV Production (MWh): %s' % (PV_year))

        plt.subplot(3, 1, 3)
        plt.bar(
            range(len(RES_monthly)),
            list(RES_monthly.values()),
            align='center')
        plt.xticks(range(len(RES_monthly)), list(RES_monthly.keys()))
        plt.yticks()
        plt.ylabel('Energy (kWh)')
        plt.title('Total RES Production (MWh): %s' % (RES_year))

        plt.tight_layout()
        fig.savefig(fileout, format='png', dpi=FIG_DPI, bbox_inches='tight')
        plt.close()


class Calcs(object):

    def __init__(self, root: Path, subname: str, results: Dict[str, pd.DataFrame]):

        self.root = Path(root).resolve()
        self.folder_path = self.root / OUTDIR / subname
        self.subname = subname
        self.results = results[subname]

        self.myInputs = inputs.Inputs(self.root, subname)
        # controller inputs
        controller_info = self.myInputs.controller()['controller_info']
        self.timesteps = controller_info['total_timesteps']
        self.first_hour = controller_info['first_hour']

    # technical outputs

    def max_heat_pump_output(self):

        results = self.results
        timesteps = self.timesteps

        HPt = np.zeros(timesteps)

        for i in range(timesteps):
            HPt[i] = results[i]['HP']['heat_total_output']

        max_HPt = np.amax(HPt)

        return max_HPt

    def max_heat_demand(self):

        results = self.results
        timesteps = self.timesteps

        hd = np.zeros(timesteps)

        for i in range(timesteps):
            hd[i] = results[i]['heat_demand']['heat_demand']

        max_hd = np.amax(hd)

        return max_hd

    def sum_aux_output(self):

        results = self.results
        timesteps = self.timesteps

        aux = np.zeros(timesteps)

        for i in range(timesteps):
            aux[i] = results[i]['aux']['demand']

        sum_aux = np.sum(aux)

        return sum_aux

    def sum_hp_output(self):

        results = self.results
        timesteps = self.timesteps

        HPt = np.zeros(timesteps)

        for i in range(timesteps):
            HPt[i] = results[i]['HP']['heat_total_output']

        sum_HPt = np.sum(HPt)

        return sum_HPt

    def sum_hp_usage(self):

        results = self.results
        timesteps = self.timesteps

        HPe = np.zeros(timesteps)

        for i in range(timesteps):
            HPe[i] = results[i]['HP']['elec_total_usage']

        sum_HPe = np.sum(HPe)

        return sum_HPe

    def calc_scop(self):

        scop = self.sum_hp_output() / self.sum_hp_usage()
        return scop

    def sum_hd(self):

        results = self.results
        timesteps = self.timesteps

        hd = np.zeros(timesteps)

        for i in range(timesteps):
            hd[i] = results[i]['heat_demand']['heat_demand']

        sum_hd = np.sum(hd)

        return sum_hd

    def sum_ed(self):

        results = self.results
        timesteps = self.timesteps

        ed = np.zeros(timesteps)

        for i in range(timesteps):
            ed[i] = results[i]['elec_demand']['elec_demand']

        sum_ed = np.sum(ed)

        return sum_ed

    def sum_ed_import(self):

        results = self.results
        timesteps = self.timesteps

        ed = np.zeros(timesteps)

        for i in range(timesteps):
            ed[i] = results[i]['grid']['import_for_elec_demand']

        sum_ed = np.sum(ed)

        return sum_ed

    def sum_ed_RES(self):

        results = self.results
        timesteps = self.timesteps

        ed = np.zeros(timesteps)

        for i in range(timesteps):
            ed[i] = results[i]['RES']['elec_demand']

        sum_ed = np.sum(ed)

        return sum_ed

    def sum_import(self):

        results = self.results
        timesteps = self.timesteps

        imp = np.zeros(timesteps)

        for i in range(timesteps):
            imp[i] = results[i]['grid']['total_import']

        sum_imp = np.sum(imp)

        return sum_imp

    def sum_export(self):

        results = self.results
        timesteps = self.timesteps

        exp = np.zeros(timesteps)

        for i in range(timesteps):
            exp[i] = results[i]['grid']['total_export']

        sum_exp = np.sum(exp)

        return sum_exp

    def sum_RES(self):

        results = self.results
        timesteps = self.timesteps

        RES = np.zeros(timesteps)

        for i in range(timesteps):
            RES[i] = results[i]['RES']['generation_total']

        sum_RES = np.sum(RES)

        return sum_RES

    # technical KPIs

    def HP_size_ratio(self):

        # look over whole period
        # find highest heat pump thermal output
        # find highest heat demand
        # max hd / max hpto = plant size change
        # return percentage

        max_HPt = self.max_heat_pump_output()
        max_hd = self.max_heat_demand()

        return round(max_HPt / max_hd, 2)

    def HP_utilisation(self):

        sum_hp = self.sum_hp_output()
        sum_hd = self.sum_hd()

        ratio = sum_hp / sum_hd

        return round(ratio, 2) * 100

    def RES_self_consumption(self):

        _sum_RES = self.sum_RES()
        _sum_export = self.sum_export()

        if _sum_RES > 0:
            ratio = 1 - _sum_export / float(_sum_RES)
        else:
            ratio = 0

        return ratio * 100

    def total_RES_self_consumption(self):

        _sum_RES = self.sum_RES() - self.sum_export()

        return _sum_RES

    def grid_RES_used(self):

        subname = self.subname

        results = self.results
        timesteps = self.timesteps
        # what is the discount price?
        grid_inputs = self.myInputs.grid()
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

            return 0.

        elif tariff_choice == 'Variable periods':

            return 0.

        elif tariff_choice == 'Time of use - WM':

            return 0.

        elif tariff_choice == 'Time of use - PPA + FR':

            fr = grid_inputs['flat_rates']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                flat_rate=fr, lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        elif tariff_choice == 'Time of use - PPA + WM':

            twm = grid_inputs['wholesale_market']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                wholesale_market=twm, premium=premium,
                maximum=maximum, lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        elif tariff_choice == 'Time of use - PPA + VP':

            vp = grid_inputs['variable_periods']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                variable_periods=vp,
                variable_periods_year=variable_periods_year,
                lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        wind_farm = myGrid.wind_farm_info()
        higher_band = wind_farm['higher_band']
        power = wind_farm['power']

        grid_RES_import = np.zeros(timesteps)
        for i in range(timesteps):
            if power[i] >= higher_band:
                grid_RES_import[i] = (
                    results[i]['grid']['total_import'])
            else:
                grid_RES_import[i] = 0.

        return np.sum(grid_RES_import)

    def heat_grid_RES_used(self):

        subname = self.subname

        results = self.results
        timesteps = self.timesteps
        # what is the discount price?
        grid_inputs = self.myInputs.grid()
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

            return 0.

        elif tariff_choice == 'Variable periods':

            return 0.

        elif tariff_choice == 'Time of use - WM':

            return 0.

        elif tariff_choice == 'Time of use - PPA + FR':

            fr = grid_inputs['flat_rates']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                flat_rate=fr, lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        elif tariff_choice == 'Time of use - PPA + WM':

            twm = grid_inputs['wholesale_market']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                wholesale_market=twm, premium=premium,
                maximum=maximum, lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        elif tariff_choice == 'Time of use - PPA + VP':

            vp = grid_inputs['variable_periods']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                variable_periods=vp,
                variable_periods_year=variable_periods_year,
                lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        wind_farm = myGrid.wind_farm_info()
        higher_band = wind_farm['higher_band']
        power = wind_farm['power']

        grid_RES_import = np.zeros(timesteps)
        for i in range(timesteps):
            if power[i] >= higher_band:
                grid_RES_import[i] = (
                    results[i]['aux']['demand'] - results[i]['RES']['aux'] +
                    results[i]['HP']['elec_import_usage'])
            else:
                grid_RES_import[i] = 0.

        return np.sum(grid_RES_import)

    def heat_from_grid_RES(self):

        subname = self.subname

        results = self.results
        timesteps = self.timesteps
        # what is the discount price?
        grid_inputs = self.myInputs.grid()
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

            return 0.

        elif tariff_choice == 'Variable periods':

            return 0.

        elif tariff_choice == 'Time of use - WM':

            return 0.

        elif tariff_choice == 'Time of use - PPA + FR':

            fr = grid_inputs['flat_rates']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                flat_rate=fr, lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        elif tariff_choice == 'Time of use - PPA + WM':

            twm = grid_inputs['wholesale_market']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                wholesale_market=twm, premium=premium,
                maximum=maximum, lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        elif tariff_choice == 'Time of use - PPA + VP':

            vp = grid_inputs['variable_periods']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                variable_periods=vp,
                variable_periods_year=variable_periods_year,
                lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        wind_farm = myGrid.wind_farm_info()
        higher_band = wind_farm['higher_band']
        power = wind_farm['power']

        grid_RES_import = np.zeros(timesteps)
        for i in range(timesteps):
            if power[i] >= higher_band:
                grid_RES_import[i] = (
                    results[i]['aux']['demand'] - results[i]['RES']['aux'] +
                    results[i]['HP']['elec_import_usage'] *
                    results[i]['HP']['cop'])
            else:
                grid_RES_import[i] = 0.

        return np.sum(grid_RES_import)

    def HP_from_grid_RES(self):

        subname = self.subname

        results = self.results
        timesteps = self.timesteps
        # what is the discount price?
        grid_inputs = self.myInputs.grid()
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

            return 0.

        elif tariff_choice == 'Variable periods':

            return 0.

        elif tariff_choice == 'Time of use - WM':

            return 0.

        elif tariff_choice == 'Time of use - PPA + FR':

            fr = grid_inputs['flat_rates']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                flat_rate=fr, lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        elif tariff_choice == 'Time of use - PPA + WM':

            twm = grid_inputs['wholesale_market']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                wholesale_market=twm, premium=premium,
                maximum=maximum, lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        elif tariff_choice == 'Time of use - PPA + VP':

            vp = grid_inputs['variable_periods']
            myGrid = grid.Grid(
                self.root, subname, export,
                tariff_choice, balancing_mechanism, grid_services,
                variable_periods=vp,
                variable_periods_year=variable_periods_year,
                lower_percent=lower_percent,
                higher_percent=higher_percent, higher_discount=higher_discount,
                lower_penalty=lower_penalty)

        wind_farm = myGrid.wind_farm_info()
        higher_band = wind_farm['higher_band']
        power = wind_farm['power']

        grid_RES_import = np.zeros(timesteps)
        for i in range(timesteps):
            if power[i] >= higher_band:
                grid_RES_import[i] = (
                    results[i]['HP']['elec_import_usage'] *
                    results[i]['HP']['cop'])
            else:
                grid_RES_import[i] = 0.

        return np.sum(grid_RES_import)

    def heat_from_local_RES(self):

        results = self.results
        timesteps = self.timesteps

        aux_res = np.zeros(timesteps)
        hp_res = np.zeros(timesteps)

        for i in range(timesteps):
            aux_res[i] = results[i]['RES']['aux']
            hp_res[i] = (
                results[i]['HP']['elec_RES_usage'] *
                results[i]['HP']['cop'])

        tot = np.sum(aux_res) + np.sum(hp_res)

        return tot

    def HP_from_local_RES(self):

        results = self.results
        timesteps = self.timesteps

        hp_res = np.zeros(timesteps)

        for i in range(timesteps):
            hp_res[i] = (
                results[i]['HP']['elec_RES_usage'] *
                results[i]['HP']['cop'])

        tot = np.sum(hp_res)

        return tot

    def HP_total_RES_used(self):
        tot = (
            self.HP_from_local_RES() +
            self.HP_from_grid_RES())
        return tot

    def total_RES_used(self):
        tot = self.grid_RES_used() + self.total_RES_self_consumption()
        return tot

    def heat_total_RES_used(self):

        tot = (
            self.heat_grid_RES_used() +
            self.total_RES_self_consumption() -
            self.sum_ed_RES())
        return tot

    def demand_met_RES(self):
        # sum the heat pump elec usage, demand from aux usage,
        # and elec demand usage
        # percentage of this from RES used

        demand = self.sum_hp_usage() + self.sum_aux_output() + self.sum_ed()
        RES_used = self.total_RES_used()

        dmRES = (1 - (demand - RES_used) / demand) * 100
        return dmRES

    def heat_met_RES(self):
        # sum the heat pump elec usage, demand from aux usage,
        # percentage of this from RES used

        demand = self.sum_hp_output() + self.sum_aux_output()
        # demand = self.sum_hd()
        RES_used = self.heat_from_local_RES() + self.heat_from_grid_RES()

        dmRES = RES_used / demand * 100
        return dmRES

    def HP_met_RES(self):
        # sum the heat pump elec usage, demand from aux usage,
        # percentage of this from RES used

        demand = self.sum_hp_output()
        RES_used = self.HP_from_local_RES() + self.HP_from_grid_RES()

        dmRES = RES_used / demand * 100
        return dmRES

    def days_storage_content(self):

        # factor for counting for when not simulating whole year
        f = self.timesteps / 8760
        av_day_demand = self.sum_hd() / (365 * f)

        str = self.subname
        str = str.replace("_", " ")
        t = [int(s) for s in str.split() if s.isdigit()]
        capacity = t[1]
        # presuming a delta t of 20
        energy = capacity * 4.18 * 20 / 3600

        day_content = energy / av_day_demand
        return day_content

    # economic KPIs

    def RHI_income(self):

        HP_sum = self.sum_hp_output()
        HPe_sum = self.sum_hp_usage()
        HP_eligble = HP_sum - HPe_sum

        str = self.subname
        str = str.replace("_", " ")
        t = [int(s) for s in str.split() if s.isdigit()]
        HP_capacity = t[0]
        RHI_info = self.myInputs.RHI()

        if RHI_info['tariff_type'] == 'Fixed':
            year_income = HP_eligble * RHI_info['fixed_rate'] / 100.

        elif RHI_info['tariff_type'] == 'Tiered':
            tier_1_output = HP_capacity * 1314
            if HP_eligble <= tier_1_output:
                year_income = HP_eligble * RHI_info['tier_1'] / 100.
            elif HP_eligble > tier_1_output:
                year_income = (
                    (tier_1_output * RHI_info['tier_1'] +
                     (HP_eligble - tier_1_output) * RHI_info['tier_2']) /
                    100.)

        if RHI_info['RHI_type'] == 'Domestic':
            years = 7.
        elif RHI_info['RHI_type'] == 'Non-domestic':
            years = 20.

        # units are pounds
        total_income = year_income * years

        return {'year_income': year_income, 'total_income': total_income}

    def capital_cost(self):

        # pound / kW
        # hp_capex = 550
        hp_capex = 600
        # pound / L
        # ts_capex = 3

        def ts_calc(ts_size):
            # see the excel sheet for the line fitting
            # 'thermal_storage_costs.xlsx'
            # pound / metre cubed
            if ts_size <= 0.0:
                return 0.0
            return 7479.1 * ((ts_size / 1000.0) ** (-0.501))

        str = self.subname
        str = str.replace("_", " ")
        t = [int(s) for s in str.split() if s.isdigit()]
        hp_size = t[0]
        ts_size = t[1]

        capex = hp_size * hp_capex + ts_size * ts_calc(ts_size) / 1000
        # capex = hp_size * hp_capex + ts_size * ts_capex

        return capex / 1000.

    def operating_cost(self):

        # operating cost includes covering
        # electrical and thermal demand

        results = self.results
        timesteps = self.timesteps

        cashflow = np.zeros(timesteps)
        aux_cost = np.zeros(timesteps)

        for i in range(timesteps):
            cashflow[i] = results[i]['grid']['cashflow']
            aux_cost[i] = results[i]['aux']['cost'] / 1000.

        # different for electric aux/non electric aux
        # with electric aux cost included in import

        if self.myInputs.aux()['fuel'] == 'Electric':
            opex = np.sum(-cashflow)
        else:
            opex = np.sum(-cashflow) + np.sum(aux_cost)

        return opex / 1000

    def cost_of_heat(self):

        results = self.results
        timesteps = self.timesteps

        heat_cost = np.zeros(timesteps)

        if self.myInputs.aux()['fuel'] == 'Electric':
            for i in range(timesteps):
                heat_cost[i] = (
                    (results[i]['grid']['total_import'] -
                     results[i]['grid']['import_for_elec_demand']) *
                    results[i]['grid']['import_price'] / 1000.)

        else:
            for i in range(timesteps):
                heat_cost[i] = (
                    ((results[i]['grid']['total_import'] -
                     results[i]['grid']['import_for_elec_demand']) *
                     results[i]['grid']['import_price'] / 1000.) +
                    results[i]['aux']['cost'] / 1000.)

        # total heat output from aux and heatpump
        aux_tot = self.sum_aux_output()
        hp_tot = self.sum_hp_output()
        heat_cost_tot = np.sum(heat_cost)
        RHI = self.RHI_income()['year_income']

        COH = (heat_cost_tot - RHI) / (aux_tot + hp_tot)

        return COH

    def levelised_cost_of_heat(self):

        results = self.results
        timesteps = self.timesteps

        heat_cost = np.zeros(timesteps)

        if self.myInputs.aux()['fuel'] == 'Electric':
            for i in range(timesteps):
                heat_cost[i] = (
                    (results[i]['grid']['total_import'] -
                     results[i]['grid']['import_for_elec_demand']) *
                    results[i]['grid']['import_price'] / 1000.)

        else:
            for i in range(timesteps):
                heat_cost[i] = (
                    (results[i]['grid']['total_import'] -
                     results[i]['grid']['import_for_elec_demand']) *
                    results[i]['grid']['import_price'] / 1000. +
                    results[i]['aux']['cost'] / 1000)

        # capital cost + operating cost divided by total energy output
        capex = self.capital_cost() * 1000
        heat_cost_tot = np.sum(heat_cost)
        RHI = self.RHI_income()['total_income']

        # total heat output from aux and heatpump
        hd = self.sum_hd()

        # factor for counting for when not simulating whole year
        f = 8760 / self.timesteps

        # assuming 20 year life
        LCOH = (
            ((capex + heat_cost_tot * f * 20) - RHI) /
            ((hd) * f * 20))

        return LCOH

    def levelised_cost_of_energy(self):

        results = self.results
        timesteps = self.timesteps

        cashflow = np.zeros(timesteps)

        if self.myInputs.aux()['fuel'] == 'Electric':
            for i in range(timesteps):
                cashflow[i] = (
                    (-results[i]['grid']['cashflow'] / 1000.))

        else:
            for i in range(timesteps):
                cashflow[i] = (
                    (-results[i]['grid']['cashflow'] / 1000. +
                     results[i]['aux']['cost'] / 1000))

        # capital cost + operating cost divided by total energy output
        capex = self.capital_cost() * 1000
        energy_cost_tot = np.sum(cashflow) * 1000
        RHI = self.RHI_income()['total_income']

        # total energy output from heat pump, elec demand met and aux
        heat_dem = self.sum_hd()
        elec_dem = self.sum_ed()

        # factor for counting for when not simulating whole year
        f = 8760 / self.timesteps

        # assuming 20 year life
        LCOE = (
            ((capex + energy_cost_tot * f * 20) - RHI) /
            ((heat_dem + elec_dem) * f * 20))

        return LCOE

    def cost_elec(self):

        results = self.results
        timesteps = self.timesteps

        elec_cost = np.zeros(timesteps)

        for i in range(timesteps):
            elec_cost[i] = (
                (-results[i]['grid']['cashflow'] / 1000.))

        return np.sum(elec_cost)

    def lifetime_cost(self):

        results = self.results
        timesteps = self.timesteps

        energy_cost = np.zeros(timesteps)

        if self.myInputs.aux()['fuel'] == 'Electric':
            for i in range(timesteps):
                energy_cost[i] = (
                    (-results[i]['grid']['cashflow'] / 1000.))

        else:
            for i in range(timesteps):
                energy_cost[i] = (
                    (-results[i]['grid']['cashflow'] / 1000. +
                     results[i]['aux']['cost'] / 1000))

        # capital cost + operating cost divided by total energy output
        capex = self.capital_cost()
        energy_cost_tot = np.sum(energy_cost)

        # factor for counting for when not simulating whole year
        f = 8760 / self.timesteps

        # assuming 20 year life
        life_cost = (
            (capex + energy_cost_tot * f * 20))

        return life_cost


class ThreeDPlots(object):

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        # folder path name is in main name alongside parametric solutions
        self.folder_path = self.root / OUTDIR / 'KPIs'

        # creates a folder for keeping all the
        # pickle input files as saved from the excel file
        if self.folder_path.is_dir() is False:
            self.folder_path.mkdir()

        elif self.folder_path.is_dir() is True:
            shutil.rmtree(self.folder_path)
            self.folder_path.mkdir()

        # read in set of parameters from input
        file1 = self.root / INDIR / "inputs.pkl"
        self.input = pd.read_pickle(file1)
        pa = self.input['parametric_analysis']
        # list set of heat pump sizes
        hp_sizes = []
        # if no step then only one size looked at
        if pa['hp_min'] == pa['hp_max']:
            hp_sizes.append(pa['hp_min'])
        else:
            for i in range(pa['hp_min'], pa['hp_max'] + pa['hp_step'], pa['hp_step']):
                hp_sizes.append(i)
        # list sizes of ts
        ts_sizes = []
        # if no step then only one size looked at
        if pa['ts_min'] == pa['ts_max']:
            ts_sizes.append(pa['ts_min'])
        else:
            for i in range(pa['ts_min'], pa['ts_max'] + pa['hp_step'], pa['ts_step']):
                ts_sizes.append(i)
        combos = []
        for i in range(len(hp_sizes)):
            for j in range(len(ts_sizes)):
                combos.append([hp_sizes[i], ts_sizes[j]])
        self.combos = combos

        # strings for all combos to READ OUTPUTS
        results = {}
        subnames = []
        for i in range(len(combos)):
            subname = 'hp_' + str(combos[i][0]) + '_ts_' + str(combos[i][1])
            subnames.append(subname)
            # read pickle output file
            file_output_pickle = self.root / OUTDIR / subname / 'outputs.pkl'
            results[subname] = pd.read_pickle(file_output_pickle)
        self.results = results
        self.subnames = subnames

    def heat_pump_sizes_x(self):

        hp_sizes = []
        for i in range(len(self.combos)):
            hp_sizes.append(self.combos[i][0])
        return hp_sizes

    def thermal_store_sizes_y(self):

        ts_sizes = []
        for i in range(len(self.combos)):
            ts_sizes.append(self.combos[i][1] / 1000.)
        return ts_sizes

    def plot_opex(self):

        opex = []

        for x in range(len(self.subnames)):
            _opex = Calcs(
                self.root, self.subnames[x],
                self.results).operating_cost()
            opex.append(_opex)

        z = opex

        plt.style.use('classic')

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        y = self.heat_pump_sizes_x()
        x = self.thermal_store_sizes_y()

        ax.plot_trisurf(x, y, z, linewidth=0, antialiased=False,
                        cmap=plt.cm.Spectral)
        ax.set_xlabel('Thermal storage capacity ($m^3$)', fontsize=10)
        ax.set_ylabel('Heat pump sizes (kW)', fontsize=10)
        ax.set_zlabel(u'Operational cost (k\u00a3)', fontsize=10)
        ax.xaxis.labelpad = 15
        ax.yaxis.labelpad = 15
        ax.zaxis.labelpad = 15
        # plt.show()
        # ax.invert_yaxis()

        plt.tight_layout()

        fileout = self.folder_path / 'operating_cost.png'
        fig.savefig(fileout, format='png', dpi=FIG_DPI)
        plt.close()

    def plot_RES(self):

        RES_used = []

        for x in range(len(self.subnames)):
            _RES_used = Calcs(
                self.root, self.subnames[x],
                self.results).RES_self_consumption()
            RES_used.append(_RES_used)

        z = RES_used

        plt.style.use('classic')

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        x = self.heat_pump_sizes_x()
        y = self.thermal_store_sizes_y()

        ax.plot_trisurf(x, y, z, linewidth=0, antialiased=False,
                        cmap=plt.cm.Spectral)

        ax.set_xlabel('Heat pump sizes (kW)', fontsize=10)
        ax.set_ylabel('Thermal storage capacity ($m^3$)', fontsize=10)
        ax.set_zlabel('RES self-consumption (%)', fontsize=10)
        ax.xaxis.labelpad = 15
        ax.yaxis.labelpad = 15
        ax.zaxis.labelpad = 15
        # plt.show()
        plt.tight_layout()

        fileout = self.folder_path / 'RES_self_consumption.png'
        fig.savefig(fileout, format='png', dpi=FIG_DPI)
        plt.close()

    def plot_heat_from_RES(self):

        RES_used = []

        for x in range(len(self.subnames)):
            _RES_used = Calcs(
                self.root, self.subnames[x],
                self.results).heat_met_RES()
            RES_used.append(_RES_used)

        z = RES_used

        plt.style.use('classic')

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        x = self.heat_pump_sizes_x()
        y = self.thermal_store_sizes_y()

        ax.plot_trisurf(x, y, z, linewidth=0, antialiased=False,
                        cmap=plt.cm.Spectral)

        ax.set_xlabel('Heat pump sizes (kW)', fontsize=10)
        ax.set_ylabel('Thermal storage capacity ($m^3$)', fontsize=10)
        ax.set_zlabel('Heat demand from RES (%)', fontsize=10)
        ax.xaxis.labelpad = 15
        ax.yaxis.labelpad = 15
        ax.zaxis.labelpad = 15
        # plt.show()
        plt.tight_layout()

        fileout = self.folder_path / 'heat_from_RES.png'
        fig.savefig(fileout, format='png', dpi=FIG_DPI)
        plt.close()

    def plot_HP_size_ratio(self):

        HP_size_ratio = []

        for x in range(len(self.subnames)):
            _HP_size_ratio = Calcs(
                self.root, self.subnames[x],
                self.results).HP_size_ratio()
            HP_size_ratio.append(_HP_size_ratio)

        z = HP_size_ratio

        plt.style.use('classic')

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        y = self.heat_pump_sizes_x()
        x = self.thermal_store_sizes_y()

        ax.plot_trisurf(x, y, z, linewidth=0, antialiased=False,
                        cmap=plt.cm.Spectral)
        ax.invert_xaxis()
        ax.set_xlabel('Thermal storage capacity ($m^3$)', fontsize=10)
        ax.set_ylabel('Heat pump sizes (kW)', fontsize=10)
        ax.set_zlabel('HP size ratio', fontsize=10)
        ax.xaxis.labelpad = 15
        ax.yaxis.labelpad = 15
        ax.zaxis.labelpad = 15
        # plt.show()
        plt.tight_layout()

        fileout = self.folder_path / 'HP_size_ratio.png'
        fig.savefig(fileout, format='png', dpi=FIG_DPI)
        plt.close()

    def plot_HP_utilisation(self):

        HP_utilisation = []

        for x in range(len(self.subnames)):
            _HP_utilisation = Calcs(
                self.root, self.subnames[x],
                self.results).HP_utilisation()
            HP_utilisation.append(_HP_utilisation)

        z = HP_utilisation

        plt.style.use('classic')

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        y = self.heat_pump_sizes_x()
        x = self.thermal_store_sizes_y()

        ax.plot_trisurf(x, y, z, linewidth=0, antialiased=False,
                        cmap=plt.cm.Spectral)
        ax.invert_xaxis()

        ax.set_xlabel('Thermal storage capacity ($m^3$)', fontsize=10)
        ax.set_ylabel('Heat pump sizes (kW)', fontsize=10)
        ax.set_zlabel('HP utilisation (%)', fontsize=10)
        ax.xaxis.labelpad = 15
        ax.yaxis.labelpad = 15
        ax.zaxis.labelpad = 15
        # plt.show()
        plt.tight_layout()

        fileout = self.folder_path / 'HP_utilisation.png'
        fig.savefig(fileout, format='png', dpi=FIG_DPI)
        plt.close()

    def plot_capital_cost(self):

        capital_cost = []

        for x in range(len(self.subnames)):
            _capital_cost = Calcs(
                self.root, self.subnames[x],
                self.results).capital_cost()
            capital_cost.append(_capital_cost)

        z = capital_cost

        plt.style.use('classic')

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        y = self.heat_pump_sizes_x()
        x = self.thermal_store_sizes_y()

        ax.plot_trisurf(x, y, z, linewidth=0, antialiased=False,
                        cmap=plt.cm.Spectral)
        ax.invert_xaxis()
        ax.set_xlabel('Thermal storage capacity ($m^3$)', fontsize=10)
        ax.set_ylabel('Heat pump sizes (kW)', fontsize=10)
        ax.set_zlabel(u'Capital cost (k\u00a3)', fontsize=10)
        ax.xaxis.labelpad = 15
        ax.yaxis.labelpad = 15
        ax.zaxis.labelpad = 15
        # plt.show()
        plt.tight_layout()

        fileout = self.folder_path / 'capital_cost.png'
        fig.savefig(fileout, format='png', dpi=FIG_DPI)
        plt.close()

    def plot_COH(self):

        cost_of_heat = []

        for x in range(len(self.subnames)):
            _cost_of_heat = Calcs(
                self.root, self.subnames[x],
                self.results).cost_of_heat()
            cost_of_heat.append(_cost_of_heat)

        z = cost_of_heat

        plt.style.use('classic')

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        y = self.heat_pump_sizes_x()
        x = self.thermal_store_sizes_y()

        ax.plot_trisurf(x, y, z, linewidth=0, antialiased=False,
                        cmap=plt.cm.Spectral)

        ax.set_xlabel('Thermal storage capacity ($m^3$)', fontsize=10)
        ax.set_ylabel('Heat pump sizes (kW)', fontsize=10)
        ax.set_zlabel(u'Cost of heat (\u00a3/kWh)', fontsize=10)
        ax.xaxis.labelpad = 15
        ax.yaxis.labelpad = 15
        ax.zaxis.labelpad = 15
        # ax.invert_yaxis()
        # plt.show()
        plt.tight_layout()

        fileout = self.folder_path / 'cost_of_heat.png'
        fig.savefig(fileout, format='png', dpi=FIG_DPI)
        plt.close()

    def plot_LCOH(self):

        levelised_cost_of_heat = []

        for x in range(len(self.subnames)):
            _levelised_cost_of_heat = Calcs(
                self.root, self.subnames[x],
                self.results).levelised_cost_of_heat()
            levelised_cost_of_heat.append(_levelised_cost_of_heat)

        z = levelised_cost_of_heat

        plt.style.use('classic')

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        y = self.heat_pump_sizes_x()
        x = self.thermal_store_sizes_y()

        ax.plot_trisurf(x, y, z, linewidth=0, antialiased=False,
                        cmap=plt.cm.Spectral)

        ax.set_xlabel('Thermal storage capacity ($m^3$)', fontsize=10)
        ax.set_ylabel('Heat pump sizes (kW)', fontsize=10)
        ax.set_zlabel(u'Levelised cost of heat (\u00a3/kWh)', fontsize=10)
        ax.xaxis.labelpad = 15
        ax.yaxis.labelpad = 15
        ax.zaxis.labelpad = 15
        # ax.invert_yaxis()
        # plt.show()
        plt.tight_layout()

        fileout = self.folder_path / 'levelised_cost_of_heat.png'
        fig.savefig(fileout, format='png', dpi=FIG_DPI)
        plt.close()

    def KPIs_to_csv(self):

        hp_sizes = self.heat_pump_sizes_x()
        ts_sizes = self.thermal_store_sizes_y()

        opex = np.zeros(len(self.subnames))
        RES_used = np.zeros(len(self.subnames))
        total_RES_self_consumption = np.zeros(len(self.subnames))
        grid_RES_used = np.zeros(len(self.subnames))
        total_RES_used = np.zeros(len(self.subnames))
        HP_size_ratio = np.zeros(len(self.subnames))
        HP_utilisation = np.zeros(len(self.subnames))
        capital_cost = np.zeros(len(self.subnames))
        cost_of_heat = np.zeros(len(self.subnames))
        levelised_cost_of_heat = np.zeros(len(self.subnames))
        levelised_cost_of_energy = np.zeros(len(self.subnames))
        cost_elec = np.zeros(len(self.subnames))
        lifetime_cost = np.zeros(len(self.subnames))
        sum_hp_output = np.zeros(len(self.subnames))
        sum_hp_usage = np.zeros(len(self.subnames))
        scop = np.zeros(len(self.subnames))
        sum_aux_output = np.zeros(len(self.subnames))
        sum_ed_import = np.zeros(len(self.subnames))
        sum_RES = np.zeros(len(self.subnames))
        sum_import = np.zeros(len(self.subnames))
        sum_export = np.zeros(len(self.subnames))
        demand_met_RES = np.zeros(len(self.subnames))
        HP_met_RES = np.zeros(len(self.subnames))
        days_storage_content = np.zeros(len(self.subnames))
        heat_met_RES = np.zeros(len(self.subnames))

        for x in range(len(self.subnames)):

            myCalcs = Calcs(self.root, self.subnames[x], self.results)

            opex[x] = myCalcs.operating_cost()
            RES_used[x] = myCalcs.RES_self_consumption()
            total_RES_self_consumption[x] = myCalcs.total_RES_self_consumption()
            grid_RES_used[x] = myCalcs.grid_RES_used()
            total_RES_used[x] = myCalcs.total_RES_used()
            HP_size_ratio[x] = myCalcs.HP_size_ratio()
            HP_utilisation[x] = myCalcs.HP_utilisation()
            capital_cost[x] = myCalcs.capital_cost()
            cost_of_heat[x] = myCalcs.cost_of_heat()
            levelised_cost_of_heat[x] = myCalcs.levelised_cost_of_heat()
            levelised_cost_of_energy[x] = myCalcs.levelised_cost_of_energy()
            cost_elec[x] = myCalcs.cost_elec()
            lifetime_cost[x] = myCalcs.lifetime_cost()
            sum_hp_output[x] = myCalcs.sum_hp_output()
            sum_hp_usage[x] = myCalcs.sum_hp_usage()
            scop[x] = myCalcs.calc_scop()
            sum_aux_output[x] = myCalcs.sum_aux_output()
            sum_ed_import[x] = myCalcs.sum_ed_import()
            sum_RES[x] = myCalcs.sum_RES()
            sum_import[x] = myCalcs.sum_import()
            sum_export[x] = myCalcs.sum_export()
            demand_met_RES[x] = myCalcs.demand_met_RES()
            HP_met_RES[x] = myCalcs.HP_met_RES()
            days_storage_content[x] = myCalcs.days_storage_content()
            heat_met_RES[x] = myCalcs.heat_met_RES()

        economic_data = np.array(
            [hp_sizes, ts_sizes,
             capital_cost, opex, cost_of_heat,
             cost_elec, lifetime_cost,
             levelised_cost_of_heat,
             levelised_cost_of_energy])
        df = pd.DataFrame(
            economic_data)
        df = df.transpose()
        df.columns = ['hp_sizes', 'ts_sizes',
                      'capital_cost', 'opex', 'cost_of_heat',
                      'cost_elec', 'lifetime_cost',
                      'levelised_cost_of_heat',
                      'levelised_cost_of_energy'
                      ]

        pickleout = self.folder_path / ('KPI_economic_' + self.root.name + '.pkl')
        with open(pickleout, 'wb') as handle:
            pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)

        fileout = self.folder_path / ('KPI_economic_' + self.root.name + '.csv')
        df.to_csv(fileout, index=False)

        technical_data = np.array(
            [hp_sizes, ts_sizes, RES_used,
             total_RES_self_consumption,
             grid_RES_used, total_RES_used,
             heat_met_RES, demand_met_RES,
             HP_met_RES,
             HP_size_ratio, HP_utilisation,
             days_storage_content])
        df = pd.DataFrame(
            technical_data)
        df = df.transpose()
        df.columns = ['hp_sizes', 'ts_sizes', 'local_RES_used',
                      'total_RES_self_consumption',
                      'grid_RES_used', 'total_RES_used',
                      'heat_met_RES', 'demand_met_RES',
                      'HP_met_RES',
                      'HP_size_ratio', 'HP_utilisation',
                      'days_storage_content'
                      ]

        pickleout = self.folder_path / ('KPI_technical_' + self.root.name + '.pkl')
        with open(pickleout, 'wb') as handle:
            pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)

        fileout = self.folder_path / ('KPI_technical_' + self.root.name + '.csv')
        df.to_csv(fileout, index=False)

        output = np.array(
            [hp_sizes, ts_sizes,
             sum_hp_output, sum_hp_usage, scop,
             sum_aux_output, sum_ed_import, sum_RES,
             sum_import, sum_export])
        df = pd.DataFrame(
            output)
        df = df.transpose()
        df.columns = ['hp_sizes', 'ts_sizes',
                      'sum_hp_output', 'sum_hp_usage', 'scop',
                      'sum_aux_output', 'sum_ed_import', 'sum_RES',
                      'sum_import', 'sum_export'
                      ]

        pickleout = self.folder_path / ('output_' + self.root.name + '.pkl')
        with open(pickleout, 'wb') as handle:
            pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)

        fileout = self.folder_path / ('output_' + self.root.name + '.csv')
        df.to_csv(fileout, index=False)
