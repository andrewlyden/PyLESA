import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import hot_water_tank
import inputs


def validation():

    myInputs = inputs.Inputs('WWHC_FOC_WM.xlsx', 'hp_0_ts_0')
    ts_inputs = myInputs.hot_water_tank()
    weather = myInputs.weather()

    myHotWaterTank = hot_water_tank.HotWaterTank(
        ts_inputs['capacity'],
        ts_inputs['insulation'],
        ts_inputs['location'],
        ts_inputs['number_nodes'],
        ts_inputs['dimensions'],
        ts_inputs['tank_openings'],
        ts_inputs['correction_factors'],
        air_temperature=weather)
    myHotWaterTank.capacity = 50000
    myHotWaterTank.number_nodes = 5

    number_nodes = 5

    timesteps = 24
    source_delta_t = 20
    return_temp = 65

    source_temp = [85] * timesteps
    flow_temp = [85] * timesteps
    # charge_discharge = [
    #     267.81, 151.35, 185.64, 141.9, 117.67, 122.93, 44.1,
    #     -121.79, -177.77, -260.31, -282.73, -190.41, -258.12,
    #     -247.19, -203.82, -269.62, -255.76, -261.3, 35.54,
    #     64.81, 348.66, 253.03, 256.98, 158.47, 94.23, 156.9,
    #     181.67, 36.04, 68.27, -3.03, 144.47, 160.95, -101.96,
    #     71.41, 94.55, 2.3, 137.41, 108.32, 32.63, 155.31, 37.2,
    #     98.36, 115.61, 59.4, 45, 30.85, 37.39, -129.72, 137.92,
    #     26.28, -343.13, -455.03, -371.29, -475.4, -493.92, -387.26,
    #     -387.2, -443.62, -97.47, -191.56, -42.08, 52.89, -245.88,
    #     146.05, 8.76, -161.8, -38.9, -44.69, -163.02, -163.86,
    #     -25.85, -143.38, -142.88, -112.56, -187.39, -78.68, -228.52,
    #     -137.54, -162.03, -157.25, -116.14, -124.2, -135.9, -152.94,
    #     -190.34, -43.93, -73.21, -31.84, 55.54, -21.25, -18.32,
    #     70.78, 105.5, 80.06, 114.23, 133.34]

    charge_discharge = [
        746.7, 162.91, -911.22, -978.75, -416.71, 1017.14, 468.84, 370.66,
        66.3, 433.67, 310.57, -16.48, -633.96, -1727.87, -1119.85,
        -89.02, 236.63, 496.11, 1., 1., 1., -100.32, 86.75, 433.13]

    max_energy = np.zeros(timesteps)
    nodes_temp = []
    nodes_temp.append([84.36, 83.23, 81.8, 81.6, 78.52])

    for timestep in range(timesteps):

        if charge_discharge[timestep] > 0.:
            state = 'charging'
            max_energy[timestep] = myHotWaterTank.max_energy_in_out(
                state, nodes_temp[timestep],
                source_temp[timestep], flow_temp[timestep],
                return_temp, timestep)
            if abs(charge_discharge[timestep]) <= max_energy[timestep]:
                thermal_output = charge_discharge[timestep]
                demand = 0.
            else:
                thermal_output = max_energy[timestep]
                demand = 0.

        elif charge_discharge[timestep] < 0.:
            state = 'discharging'
            max_energy[timestep] = myHotWaterTank.max_energy_in_out(
                state, nodes_temp[timestep],
                source_temp[timestep], flow_temp[timestep],
                return_temp, timestep)
            if abs(charge_discharge[timestep]) <= max_energy[timestep]:
                demand = abs(charge_discharge[timestep])
                thermal_output = 0.
            else:
                demand = max_energy[timestep]
                thermal_output = 0.

        # new temps after charging/discharging
        node_temp_list = myHotWaterTank.new_nodes_temp(
            state, nodes_temp[timestep],
            source_temp[timestep], source_delta_t,
            flow_temp[timestep], return_temp,
            thermal_output, demand, timestep)
        nodes_temp.append(node_temp_list[number_nodes - 1])

    plt.style.use('ggplot')
    plt.rcParams.update({'font.size': 16})
    plt.subplot(2, 1, 1)
    plt.plot(nodes_temp)
    plt.ylabel('Node temperature \n (degC)')
    plt.title('Modelled node temperatures')
    plt.xlabel('Hour timesteps')

    # read csv file
    data = pd.read_csv('wwhc_ts.csv')
    plt.subplot(2, 1, 2)
    plt.plot(data)
    plt.ylabel('Node temperature \n (degC)')
    plt.title('Monitored node temperatures')
    plt.xlabel('15-minute timesteps')

    # plt.tight_layout()
    plt.show()


validation()


def test():

    myInputs = inputs.Inputs('WWHC_ires.xlsx', 'hp_600_ts_50000')
    ts_inputs = myInputs.hot_water_tank()
    weather = myInputs.weather()
    demands = myInputs.demands()

    myHotWaterTank = hot_water_tank.HotWaterTank(
        ts_inputs['capacity'],
        ts_inputs['insulation'],
        ts_inputs['location'],
        ts_inputs['number_nodes'],
        ts_inputs['dimensions'],
        ts_inputs['tank_openings'],
        ts_inputs['correction_factors'],
        air_temperature=weather)

    number_nodes = ts_inputs['number_nodes']

    timestep = 30
    source_delta_t = demands['source_delta_t']
    return_temp = demands['return_temp_DH']

    source_temp = demands['source_temp']
    flow_temp = demands['flow_temp_DH']

    # charging, discharging, standby
    state = 'discharging'

    if state == 'charging':
        nodes_temp = [40, 40, 40]
        demand = 0
        thermal_output = 20
    elif state == 'discharging':
        nodes_temp = [70, 70, 20]
        demand = 20
        thermal_output = 0
    elif state == 'standby':
        nodes_temp = [90, 90, 90]
        demand = 0
        thermal_output = 0

    # discharge_function = myHotWaterTank.discharging_function(
    #     state, nodes_temp, return_temp)
    # charge_function = myHotWaterTank.charging_function(
    #     state, nodes_temp, source_temp)

    # coefficients = myHotWaterTank.set_of_coefficients(
    #     state, nodes_temp, source_temp, return_temp,
    #     mass_flow, timestep)

    # for t in range(100):

    #     node_temp_list = myHotWaterTank.new_nodes_temp(
    #         state, nodes_temp, source_temp, source_delta_t,
    #         flow_temp, return_temp, thermal_output, demand,
    #         timestep)
    #     nodes_temp = node_temp_list[number_nodes]
    #     print nodes_temp

    # max_capacity = np.empty(24)
    # energy_available = []
    # nodes_temp = []
    # nodes_temp.append([40, 40, 40, 40, 40])
    # soc = []
    # max_charge = []
    # state = 'charging'

    # for timestep in range(24):

    #     max_capacity[timestep] = myHotWaterTank.max_energy_in_out(
    #         state,
    #         [return_temp, return_temp, return_temp, return_temp, return_temp],
    #         source_temp[timestep], flow_temp[timestep], return_temp, timestep)

    #     thermal_output = 74
    #     demand = 0

    #     energy_available.append(myHotWaterTank.max_energy_in_out(
    #         state, nodes_temp[timestep], source_temp[timestep],
    #         flow_temp[timestep], return_temp, timestep))
    #     print nodes_temp[timestep]
    #     node_temp_list = myHotWaterTank.new_nodes_temp(
    #         state,
    #         nodes_temp[timestep],
    #         source_temp[timestep], source_delta_t,
    #         flow_temp[timestep], return_temp, thermal_output, demand,
    #         timestep)
    #     nodes_temp.append(node_temp_list[number_nodes - 1])
    #     if timestep == 0:
    #         soc.append(0)
    #     else:
    #         soc.append(soc[timestep - 1] + thermal_output)
    #     max_charge.append(max_capacity[timestep] - soc[timestep])

    # print energy_available, 'kWh'
    # plt.plot(energy_available)
    # plt.plot(max_capacity)
    # plt.plot(soc)
    # plt.plot(max_charge)
    # plt.show()

    max_discharge = np.empty(24)
    energy_available = []
    nodes_temp = []
    nodes_temp.append([40, 40, 40, 40, 40])
    soc = []
    init_soc = []
    state = 'charging'

    for timestep in range(24):

        max_discharge[timestep] = myHotWaterTank.max_energy_in_out(
            'discharging',
            [source_temp[timestep], source_temp[timestep],
             source_temp[timestep],
             source_temp[timestep], source_temp[timestep]],
            source_temp[timestep], flow_temp[timestep], return_temp, timestep)

        thermal_output = 70
        demand = 0

        # available energy to discharge or charge
        energy_available.append(myHotWaterTank.max_energy_in_out(
            state, nodes_temp[timestep], source_temp[timestep],
            flow_temp[timestep], return_temp, timestep))
        print nodes_temp[timestep]
        # new temps after charging/discharging
        node_temp_list = myHotWaterTank.new_nodes_temp(
            state,
            nodes_temp[timestep],
            source_temp[timestep], source_delta_t,
            flow_temp[timestep], return_temp, thermal_output, demand,
            timestep)
        nodes_temp.append(node_temp_list[number_nodes - 1])

        # now calculate the soc as if it was energy
        if timestep == 0:
            # start it is full therefore it is maximum discharge
            soc.append(max_discharge[timestep])
        else:
            soc.append(soc[timestep - 1] - demand)

        avg_nodes_temp = sum(nodes_temp[timestep]) / len(nodes_temp[timestep])
        if avg_nodes_temp <= return_temp:
            soc_ratio = 0
        elif avg_nodes_temp >= source_temp[timestep]:
            soc_ratio = 1
        else:
            soc_ratio = (avg_nodes_temp - return_temp) / (source_temp[timestep] - return_temp)
        # init_soc.append(soc_ratio * max_d[timestep])

    print energy_available, 'kWh'
    print soc, 'soc'
    print init_soc, 'init_soc'
    # plt.plot(energy_available)
    plt.plot(max_discharge)
    plt.plot(soc)
    # plt.plot(init_soc)
    plt.show()

    # plt.plot(range(60), node_temp_list[0], label='T1(t)')
    # plt.plot(range(60), node_temp_list[1], label='T2(t)')
    # plt.plot(range(60), node_temp_list[2], label='T3(t)')

    # plt.ylabel('values')
    # plt.xlabel('time')
    # plt.legend(loc='best')
    # plt.show()

    # print discharge_function, 'discharge_function'
    # print charge_function, 'charge_function'
    # print coefficients, 'set of coefficients'


# test()
