import outputs
import inputs


def run_kpis():

    name = 'WWHC_FOC_RT.xlsx'
    outputs.run_KPIs(name)


run_kpis()


def WWHC():

    name = 'WWHC_FOC_VP.xlsx'
    # subname = 'hp_0_ts_50000'

    # myInputs = inputs.Inputs(name, subname)

    # controller inputs
    # controller_info = myInputs.controller()['controller_info']
    # timesteps = controller_info['total_timesteps']

    # if timesteps == 8760:
    #     for period in ['Year', 'Winter', 'Summer']:
    #         myPlots = outputs.Plot(name, subname, period)
    #         myPlots.operation()
    #         myPlots.elec_demand_and_RES()
    #         myPlots.HP_and_heat_demand()
    #         myPlots.TS()
    #         myPlots.grid()
    #         if period == 'Year':
    #             myPlots.RES_bar()
    # else:
    #     period = 'User'
    #     myPlots = outputs.Plot(name, subname, period)
    #     myPlots.operation()
    #     myPlots.elec_demand_and_RES()
    #     myPlots.HP_and_heat_demand()
    #     myPlots.TS()
    #     myPlots.grid()
    #     myPlots.RES_bar()

    # myCalcs = outputs.Calcs(name, subname)
    # print myCalcs.RHI_income()
    # print myCalcs.sum_hp_output()
    # print myCalcs.cost_of_heat()
    # myCalcs.timesteps = 48
    # print myCalcs.HP_size_ratio(), 'HP_size_ratio'
    # print myCalcs.HP_utilisation(), 'HP_utilisation'
    # print myCalcs.RES_self_consumption(), 'RES_self_consumption'
    # print myCalcs.capital_cost(), 'capital_cost'
    # print myCalcs.operating_cost(), 'operating_cost'

    my3DPlots = outputs.ThreeDPlots(name)
    my3DPlots.KPIs_to_csv()
    my3DPlots.plot_opex()
    my3DPlots.plot_RES()
    my3DPlots.plot_heat_from_RES()
    my3DPlots.plot_HP_size_ratio()
    my3DPlots.plot_HP_utilisation()
    my3DPlots.plot_capital_cost()
    my3DPlots.plot_LCOH()
    my3DPlots.plot_COH()


def findhorn_hot_water():

    name = 'west_whins_hot_water.xlsx'
    subname = 'hp_14_ts_380'
    myPlots = outputs.Plot(name, subname)

    myPlots.operation()


def findhorn_space_heating():

    name = 'west_whins_space_heating.xlsx'
    subname = 'hp_14_ts_100'
    myPlots = outputs.Plot(name, subname)

    myPlots.operation()


# WWHC()
# findhorn_space_heating()
# findhorn_hot_water()
