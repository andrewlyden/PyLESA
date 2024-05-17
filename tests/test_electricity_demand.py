import pylesa.demand.electricity_demand as e


name = 'findhorn - west whins.xlsx'
subname = 'hp_14_ts_550'

year = 2017
# hour = 26
# e.day_of_week(year, hour)
# e.year_time_series(year)
# e.profile_from_input(year, name, subname)
# e.predicted_demand(year, name, subname)
e.plot_demand()
