import pandas as pd
import numpy as np
import os
import copy
import json

# Lower and upper bounds for size classes - Class 0 is the total average across entire range of data
class_bounds = {"recip_engine": [(30, 9300), (30, 100), (100, 630), (630, 1140), (1140, 3300), (3300, 9300)],
                "micro_turbine": [(30, 1290), (30, 60), (60, 190), (190, 950), (950, 1290)],
                "combustion_turbine": [(950, 20000), (950, 1800), (1800, 3300), (3300, 5400), (5400, 7500), (7500, 14000), (14000, 20000)],
                "fuel_cell": [(30, 9300), (30, 320), (320, 1400), (1400, 9300)]}

# Count number of size classes for each prime mover
n_classes = {pm: len(class_bounds[pm]) for pm in class_bounds.keys()}

# If no size class is input, use these defaults for the API (see validators.py).
default_chp_size_class = {"recip_engine": 0,
                          "micro_turbine": 0,
                          "combustion_turbine": 0,
                          "fuel_cell": 0}

# Capacity factor assumption for converting O&M cost in $/hr to $/kW/yr
capacity_factor = 1.0

# Fraction of lower bound kW for size class that is assigned to min_allowable_kw
min_allow_frac = [0.5, 0.7, 1.0, 0.5]

# Assumptions used to get the half load performance from the full load
elec_effic_half_frac = [0.9, 0.8, 0.8, 0.9]  # NOT USED
hre_half_frac = [1.0, 1.0, 1.0, 1.0]  # NOT USED

chp_defaults_not_size_class_dependent = {
                                        'recip_engine': {
                                           'min_kw': 0,
                                           'max_kw': 10000,
                                           'min_turn_down_pct': 0.5,
                                           'max_derate_factor': 1.0,
                                           'derate_start_temp_degF': 95,
                                           'derate_slope_pct_per_degF': 0.0},
                                        'micro_turbine': {
                                            'min_kw': 0,
                                            'max_kw': 1500,
                                            'min_turn_down_pct': 0.3,
                                            'max_derate_factor': 1.0,
                                            'derate_start_temp_degF': 59,
                                            'derate_slope_pct_per_degF': 0.0},
                                        'combustion_turbine': {
                                            'min_kw': 0,
                                            'max_kw': 20000,
                                            'min_turn_down_pct': 0.5,
                                            'max_derate_factor': 1.0,
                                            'derate_start_temp_degF': 59,
                                            'derate_slope_pct_per_degF': 0.0},
                                        'fuel_cell': {
                                            'min_kw': 0,
                                            'max_kw': 10000,
                                            'min_turn_down_pct': 0.3,
                                            'max_derate_factor': 1.0,
                                            'derate_start_temp_degF': 59,
                                            'derate_slope_pct_per_degF': 0.0}
                                        }

cooling_thermal_factor_all = {"recip_engine": (0.0, 0.8, 0.8, 0.85, 0.85, 0.85),
                          "micro_turbine": 0.94,
                          "combustion_turbine": 0.90,
                          "fuel_cell": 0.94}

def create_chp_prime_mover_defaults(class_bounds, capacity_factor, elec_effic_half_frac, hre_half_frac):
    # Cost and performane data which varies based on size class
    size_class_data = process_size_class_data(class_bounds, capacity_factor, elec_effic_half_frac, hre_half_frac)

    # Input data which does not vary based on size class for each prime mover
    class_independent_data = copy.deepcopy(chp_defaults_not_size_class_dependent)

    # Duplicate non-class dependent input parameters by the number of size classes for each prime mover
    class_independent_data = {pm: {key: [class_independent_data[pm][key]] * len(class_bounds[pm])
                                   for key in class_independent_data[pm].keys()}
                                    for pm in class_independent_data.keys()}

    # Join class-specific data with class independent data
    prime_mover_defaults_all = {pm: {**size_class_data[pm], **class_independent_data[pm]} for pm in class_independent_data.keys()}

    save_directory = os.getcwd() + '/'
    json_file_name = 'chp_default_data'
    with open(save_directory + json_file_name + '.json', 'w') as fp:
        json.dump(prime_mover_defaults_all, fp)

    return prime_mover_defaults_all

# Find average values across size class for all cost and performance parameters
# TODO there is still a tweak to the recip_engine thermal efficiency for steam (index = 1) for size_class 0 and 1 that should be automated
# TODO may be some Fuel Cell tweaks coming soon
def process_size_class_data(class_bounds, capacity_factor, elec_effic_half_frac, hre_half_frac):
    # Data
    file_capex = 'CHP_CapEx_FactSheets.csv'
    file_opex = 'CHP_OpEx_Hourly.csv'
    file_elec_effic = 'CHP_ElecEffic_FullLoad.csv'
    file_hw_therm_effic = 'CHP_ThermEffic_FullLoad_HotWater.csv'
    file_steam_therm_effic = 'CHP_ThermEffic_FullLoad_Steam.csv'

    capex_per_kw_df = pd.read_csv(file_capex, index_col=0, dtype='float64', thousands=',')
    opex_per_hr_df = pd.read_csv(file_opex, index_col=0, dtype='float64', thousands=',')
    #opex_total_per_kw_rated_per_hr = opex_per_hr_df.divide(opex_per_hr_df.index, axis=0)
    #opex_total_per_kw_per_yr = opex_per_hr_df.divide(opex_per_hr_df.index, axis=0) * capacity_factor * 8760
    opex_total_per_kwh = opex_per_hr_df.divide(opex_per_hr_df.index, axis=0)
    full_elec_effic_all = pd.read_csv(file_elec_effic, index_col=0, dtype='float64',
                                                 thousands=',')
    full_hw_therm_effic_all = pd.read_csv(file_hw_therm_effic, index_col=0, dtype='float64',
                                                  thousands=',')
    full_steam_therm_effic_all = pd.read_csv(file_steam_therm_effic, index_col=0, dtype='float64',
                                                  thousands=',')

    size_class_data_all = {}
    size_class_avg_pwr = {}
    capex_class = {}
    capex_sizes = {}
    opex_class = {}
    elec_effic_full_class = {}
    hw_therm_effic_full_class = {}
    steam_therm_effic_full_class = {}
    elec_effic_half_class = {}
    hw_therm_effic_half_class = {}
    steam_therm_effic_half_class = {}
    hw_hre_full_class = {}
    steam_hre_full_class = {}
    hw_hre_half_class = {}
    steam_hre_half_class = {}
    cooling_thermal_factor = {}
    for p, pm in enumerate(full_elec_effic_all.columns):
        size_class_avg_pwr[pm] = []
        capex_class[pm] = []
        capex_sizes[pm] = []
        opex_class[pm] = []
        elec_effic_full_class[pm] = []
        hw_therm_effic_full_class[pm] = []
        steam_therm_effic_full_class[pm] = []
        hw_hre_full_class[pm] = []
        steam_hre_full_class[pm] = []
        elec_effic_half_class[pm] = []
        hw_therm_effic_half_class[pm] = []
        steam_therm_effic_half_class[pm] = []
        hw_hre_half_class[pm] = []
        steam_hre_half_class[pm] = []
        sizes_all = capex_per_kw_df[pm].dropna().index.values
        capex_all = capex_per_kw_df[pm].dropna()
        opex_all = opex_total_per_kwh[pm].dropna().values
        elec_effic_all = full_elec_effic_all[pm].dropna().values
        hw_therm_effic_all = full_hw_therm_effic_all[pm].dropna().values
        steam_therm_effic_all = full_steam_therm_effic_all[pm].dropna().values
        cooling_thermal_factor[pm] = []
        for i, sc in enumerate(class_bounds[pm]):
            size_class_avg_pwr[pm].append(np.mean(class_bounds[pm][i]))
            #capex_class[pm].append(np.mean(capex_all[(sizes_all >= sc[0]) & (sizes_all <= sc[1])]))
            capex_class[pm].append([capex_all[sc[0]], capex_all[sc[1]]])
            capex_sizes[pm].append([sc[0], sc[1]])
            opex_class[pm].append(np.mean(opex_all[(sizes_all >= sc[0]) & (sizes_all <= sc[1])]))
            elec_effic_full_class[pm].append(np.mean(elec_effic_all[(sizes_all >= sc[0]) & (sizes_all <= sc[1])]))
            hw_therm_effic_full_class[pm].append(np.mean(hw_therm_effic_all[(sizes_all >= sc[0]) & (sizes_all <= sc[1])]))
            steam_therm_effic_full_class[pm].append(np.mean(steam_therm_effic_all[(sizes_all >= sc[0]) & (sizes_all <= sc[1])]))
            hw_hre_full_class[pm].append(hw_therm_effic_full_class[pm][i] / (1 - elec_effic_full_class[pm][i]))
            steam_hre_full_class[pm].append(steam_therm_effic_full_class[pm][i] / (1 - elec_effic_full_class[pm][i]))
            elec_effic_half_class[pm].append(elec_effic_full_class[pm][i] * elec_effic_half_frac[p])
            hw_hre_half_class[pm].append(hw_hre_full_class[pm][i] * hre_half_frac[p])
            steam_hre_half_class[pm].append(steam_hre_full_class[pm][i] * hre_half_frac[p])
            hw_therm_effic_half_class[pm].append((1 - elec_effic_half_class[pm][i]) * hw_hre_half_class[pm][i])
            steam_therm_effic_half_class[pm].append((1 - elec_effic_half_class[pm][i]) * steam_hre_half_class[pm][i])
            if pm == "recip_engine":
                if i == 0:
                    cooling_thermal_factor[pm].append(np.mean(cooling_thermal_factor_all[pm][1:])) # Ignore lowest size class value (0) in average
                elif i == 1:
                    cooling_thermal_factor[pm].append(0.0)
                else:
                    cooling_thermal_factor[pm].append(cooling_thermal_factor_all[pm][i])
            else:  # Currently cooling_thermal_factor is constant for all other prime movers, not dependent on size class
                cooling_thermal_factor[pm].append(cooling_thermal_factor_all[pm])
        # Build a dictionary of all data, grouped first by prime mover type, then by size class
        # TODO I'm putting full load efficiencies into half load efficiencies to keep constant efficiency
        size_class_data_all[pm] = {'installed_cost_us_dollars_per_kw': capex_class[pm],
                                   'tech_size_for_cost_curve': capex_sizes[pm],
                                   'om_cost_us_dollars_per_kw': [0] * len(class_bounds[pm]),
                                   'om_cost_us_dollars_per_kwh': opex_class[pm],
                                   'om_cost_us_dollars_per_hr_per_kw_rated': [0] * len(class_bounds[pm]),
                                   'elec_effic_full_load': elec_effic_full_class[pm],
                                   'elec_effic_half_load': elec_effic_full_class[pm],
                                   'thermal_effic_full_load': (hw_therm_effic_full_class[pm], steam_therm_effic_full_class[pm]),
                                   'thermal_effic_half_load': (hw_therm_effic_full_class[pm], steam_therm_effic_full_class[pm]),
                                   'min_allowable_kw': [class_bounds[pm][sc][0] * min_allow_frac[p] for sc in range(len(class_bounds[pm]))],
                                   'cooling_thermal_factor': cooling_thermal_factor[pm]}

    return size_class_data_all

processed_data = create_chp_prime_mover_defaults(class_bounds, capacity_factor, elec_effic_half_frac, hre_half_frac)

#Stop here to get processed_data
dummy = 10