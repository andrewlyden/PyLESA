import pandas as pd
import matplotlib.pyplot as plt


import pylesa.heat.heatpump as heatpump
import pylesa.io.inputs as inputs

plt.style.use('ggplot')

name = 'findhorn - west whins.xlsx'
subname = 'hp_14_ts_550'
myInputs = inputs.Inputs(name, subname)


def plot_gen_reg():

    heatpump.GenericRegression().plot_cop()


# plot_gen_reg()


def plot_cop():

    hp = heatpump.perf(name, subname)

    cop = []
    duty = []
    for time in range(8760):
        cop.append(hp[time]['cop'])
        duty.append(hp[time]['duty'])
    cop = pd.DataFrame(cop)
    duty = pd.DataFrame(duty)

    plt.plot(cop)
    plt.show()


# plot_cop()


def simple():

    inputs_basics = myInputs.heatpump_basics()
    inputs_simple = myInputs.heatpump_simple()
    inputs_demands = myInputs.demands()
    weather = myInputs.weather()

    simpleHeatPump = heatpump.HeatPump(
        inputs_basics['heat_pump_type'],
        inputs_basics['modelling_approach'],
        inputs_basics['capacity'],
        inputs_basics['ambient_delta_t'],
        inputs_basics['operation'],
        inputs_basics['minimum_output'],
        inputs_basics['data_input'],
        inputs_demands['source_temp'],
        inputs_demands['return_temp_DH'],
        weather,
        simple_cop=inputs_simple)

    print(simpleHeatPump.performance())


# simple()


def lorentz():

    inputs_basics = myInputs.heatpump_basics()
    inputs_lorentz = myInputs.heatpump_lorentz()
    inputs_demands = myInputs.demands()
    weather = myInputs.weather()

    HeatPump = heatpump.HeatPump(
        inputs_basics['heat_pump_type'],
        inputs_basics['modelling_approach'],
        inputs_basics['capacity'],
        inputs_basics['ambient_delta_t'],
        inputs_basics['operation'],
        inputs_basics['minimum_output'],
        inputs_basics['data_input'],
        inputs_demands['source_temp'],
        inputs_demands['return_temp_DH'],
        weather,
        lorentz_inputs=inputs_lorentz)

    # print(HeatPump.performance())

    HeatPump.flow_temp_source = [70] * 8760
    hp1 = HeatPump.performance()
    HeatPump.flow_temp_source = [60] * 8760
    hp2 = HeatPump.performance()

    cop1 = []
    duty1 = []
    cop2 = []
    duty2 = []
    for time in range(8760):
        cop1.append(hp1[time]['cop'])
        duty1.append(hp1[time]['duty'])
        cop2.append(hp2[time]['cop'])
        duty2.append(hp2[time]['duty'])
    cop1 = pd.DataFrame(cop1)
    duty1 = pd.DataFrame(duty1)
    cop2 = pd.DataFrame(cop2)
    duty2 = pd.DataFrame(duty2)

    plt.plot(cop1)
    plt.plot(cop2)
    plt.show()


lorentz()


def generic():

    inputs_basics = myInputs.heatpump_basics()
    inputs_demands = myInputs.demands()
    weather = myInputs.weather()

    HeatPump = heatpump.HeatPump(
        inputs_basics['heat_pump_type'],
        inputs_basics['modelling_approach'],
        inputs_basics['capacity'],
        inputs_basics['ambient_delta_t'],
        inputs_basics['operation'],
        inputs_basics['minimum_output'],
        inputs_basics['data_input'],
        inputs_demands['source_temp'],
        inputs_demands['return_temp_DH'],
        weather)

    print(HeatPump.performance())


# generic()


def standard_regression():

    myInputs = inputs.Inputs('WWHC.xlsx', 'hp_1000_ts_50000')
    inputs_basics = myInputs.heatpump_basics()
    inputs_standard_regression = myInputs.heatpump_standard_regression()
    inputs_demands = myInputs.demands()
    weather = myInputs.weather()

    HeatPump = heatpump.HeatPump(
        inputs_basics['heat_pump_type'],
        inputs_basics['modelling_approach'],
        inputs_basics['capacity'],
        inputs_basics['ambient_delta_t'],
        inputs_basics['operation'],
        inputs_basics['minimum_output'],
        inputs_basics['data_input'],
        inputs_demands['source_temp'],
        inputs_demands['return_temp_DH'],
        weather,
        standard_test_regression_inputs=inputs_standard_regression)

    HeatPump.flow_temp_source = [70] * 8760
    hp1 = HeatPump.performance()
    HeatPump.flow_temp_source = [60] * 8760
    hp2 = HeatPump.performance()

    cop1 = []
    duty1 = []
    cop2 = []
    duty2 = []
    for time in range(8760):
        cop1.append(hp1[time]['cop'])
        duty1.append(hp1[time]['duty'])
        cop2.append(hp2[time]['cop'])
        duty2.append(hp2[time]['duty'])
    cop1 = pd.DataFrame(cop1)
    duty1 = pd.DataFrame(duty1)
    cop2 = pd.DataFrame(cop2)
    duty2 = pd.DataFrame(duty2)

    plt.plot(cop1)
    plt.plot(cop2)
    plt.show()


# standard_regression()
