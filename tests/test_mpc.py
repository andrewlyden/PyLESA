import time

import pylesa.controllers.mpc as mpc

# final hour is first_hour + timesteps
# final hour must be smaller than 8760
# results are indexed from 0 to 8759 for whole year
# first_hour = 1930
# timesteps = 2000 - first_hour
# horizon = 48
# total_timesteps = horizon + timesteps


def test_solver():

    myScheduler = mpc.Scheduler(
        'WWHC_validation.xlsx', 'hp_1000_ts_50000')
    myScheduler.first_hour = 4000
    myScheduler.total_timesteps = 48
    pre_calc = myScheduler.pre_calculation()
    # print pre_calc['surplus'][4515:4539]
    # print pre_calc['max_capacity']

    hour = 0
    first_hour = 4000
    final_hour = 4048
    prev_result = {
        'HPt': 0, 'EH': 0.0,
        'TSc': 0.0, 'TSd': 0,
        'final_nodes_temp': [59.9, 53.4, 47.8, 43.5, 41.0],
        'HPtrs': 0, 'HPtrd': 0,
        'import_cost': 200}
    myScheduler.solve(pre_calc, hour, first_hour, final_hour, prev_result)


def validation():

    # myScheduler = mpc.Scheduler(
        # 'findhorn - west whins.xlsx', 'hp_14_ts_550')
    myScheduler = mpc.Scheduler(
        'WWHC_MPC_VP.xlsx', 'hp_1000_ts_300000')
    first_hour = 0
    timesteps = 168

    pre_calc = myScheduler.pre_calculation(first_hour, timesteps)
    myScheduler.moving_horizon(pre_calc, first_hour, timesteps)


def flat_rate():

    myScheduler = mpc.Scheduler(
        'WWHC_flat_rates.xlsx', 'hp_1000_ts_100000')

    pre_calc = myScheduler.pre_calculation()
    myScheduler.moving_horizon(pre_calc)


def tou():

    myScheduler = mpc.Scheduler(
        'WWHC_tou.xlsx', 'hp_1000_ts_100000')

    pre_calc = myScheduler.pre_calculation()
    myScheduler.moving_horizon(pre_calc)


def tou_PPA():

    myScheduler = mpc.Scheduler(
        'WWHC_tou_PPA.xlsx', 'hp_1000_ts_100000')

    pre_calc = myScheduler.pre_calculation()
    myScheduler.moving_horizon(pre_calc)


def flat_rate_PPA():

    myScheduler = mpc.Scheduler(
        'WWHC_flat_rates_PPA.xlsx', 'hp_1000_ts_100000')

    pre_calc = myScheduler.pre_calculation()
    myScheduler.moving_horizon(pre_calc)


def test_smallest_TS():

    myScheduler = mpc.Scheduler(
        'WWHC.xlsx', 'hp_1000_ts_100')

    pre_calc = myScheduler.pre_calculation()
    myScheduler.moving_horizon(pre_calc)


def pres(name, subname):

    myScheduler = mpc.Scheduler(
        name, subname)
    myScheduler.first_hour = 24
    myScheduler.total_timesteps = 48

    pre_calc = myScheduler.pre_calculation()
    res = myScheduler.moving_horizon(pre_calc)
    return res


# t0 = time.time()
# pres('WWHC_pres.xlsx', 'hp_500_ts_50000')
# t1 = time.time()
# tot_time = (t1 - t0) / 60.0
# print 'Input complete. Time taken: ', tot_time, 'minutes'
# test_smallest_TS()
# test_solver()
# validation()

t0 = time.time()
validation()
t1 = time.time()
tot_time = (t1 - t0) / 60.0
print('MPC complete. Time taken: ', tot_time, 'minutes')

# flat_rate()
# t0 = time.time()
# flat_rate_PPA()
# t1 = time.time()
# tot_time = (t1 - t0) / 60.0
# print 'Input complete. Time taken: ', tot_time, 'minutes'
# tou()
# tou_PPA()
