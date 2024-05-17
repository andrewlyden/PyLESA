import pylesa.controllers.fixed_order as fixed_order

first_hour = 4000
timesteps = 100
fixed_order.FixedOrder('electrical_storage.xlsx', 'hp_1000_ts_0').run_timesteps(
    first_hour, timesteps)
