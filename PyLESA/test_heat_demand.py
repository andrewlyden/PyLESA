import heat_demand as d

name = 'findhorn - west whins.xlsx'
subname = 'hp_14_ts_550'

# print d.floor_area_scaling_facotr()
# d.standard_profile_file()
# print d.standard_day_profile('top-floor-flat', 'post-2007', -2)
# print d.scaled_day_profile('top-floor-flat', 'post-2007', 3, -2)
# d.average_day_temperature(name, subname)
# d.profiles_from_inputs(name, subname)
# d.hot_water_addition(name, subname)
# d.aggregate(name, subname)
# d.predicted_demand(name, subname)
d.findhorn_demand()
