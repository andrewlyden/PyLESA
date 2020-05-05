import fixed_order

first_hour = 0
timesteps = 8760
fixed_order.FixedOrder(
    'north_whins_SH.xlsx', 'hp_5_ts_500').run_timesteps(
    first_hour, timesteps)
