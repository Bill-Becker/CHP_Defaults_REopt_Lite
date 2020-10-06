import pandas as pd
import numpy as np
import os
import copy
import json

# Lower and upper bounds for size classes - Class 0 is the total average across entire range of data
class_bounds = {"recip_engine": [(30, 9300), (30, 100), (100, 630), (630, 1140), (1140, 3300), (3300, 9300)],
                "micro_turbine": [(30, 950), (30, 60), (60, 190), (190, 950)],
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
elec_effic_half_frac = [0.9, 0.8, 0.8, 0.9]
hre_half_frac = [1.0, 1.0, 1.0, 1.0]

chp_defaults_not_size_class_dependent = {
                                        'recip_engine': {
                                           'min_kw': 0,
                                           'max_kw': 10000,
                                           'min_turn_down_pct': 0.5,
                                           'max_derate_factor': 1.0,
                                           'derate_start_temp_degF': 95,
                                           'derate_slope_pct_per_degF': 0.008},
                                        'micro_turbine': {
                                            'min_kw': 0,
                                            'max_kw': 1000,
                                            'min_turn_down_pct': 0.3,
                                            'max_derate_factor': 1.0,
                                            'derate_start_temp_degF': 59,
                                            'derate_slope_pct_per_degF': 0.012},
                                        'combustion_turbine': {
                                            'min_kw': 0,
                                            'max_kw': 20000,
                                            'min_turn_down_pct': 0.5,
                                            'max_derate_factor': 1.1,
                                            'derate_start_temp_degF': 59,
                                            'derate_slope_pct_per_degF': 0.012},
                                        'fuel_cell': {
                                            'min_kw': 0,
                                            'max_kw': 5000,
                                            'min_turn_down_pct': 0.3,
                                            'max_derate_factor': 1.0,
                                            'derate_start_temp_degF': 59,
                                            'derate_slope_pct_per_degF': 0.008}
                                        }

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

    save_directory = os.getcwd() #+ '/input_files/CHP/'
    json_file_name = 'chp_default_data'
    with open(save_directory + json_file_name + '.json', 'w') as fp:
        json.dump(prime_mover_defaults_all, fp)

    return prime_mover_defaults_all

# Find average values across size class for all cost and performance parameters
def process_size_class_data(class_bounds, capacity_factor, elec_effic_half_frac, hre_half_frac):
    # Load data
    root_dir = 'C:/Django/CHP/'
    file_capex = 'CHP_CapEx_FactSheets.csv'
    file_opex = 'CHP_OpEx_Hourly.csv'
    file_elec_effic = 'CHP_EfficFullLoad_FactSheets_All.csv'
    file_therm_effic = 'CHP_ThermEfficFullLoad_FactSheets_All.csv'

    capex_per_kw_df = pd.read_csv(root_dir + file_capex, index_col=0, dtype='float64', thousands=',')
    opex_per_hr_df = pd.read_csv(root_dir + file_opex, index_col=0, dtype='float64', thousands=',')
    #opex_total_per_kw_rated_per_hr = opex_per_hr_df.divide(opex_per_hr_df.index, axis=0)
    #opex_total_per_kw_per_yr = opex_per_hr_df.divide(opex_per_hr_df.index, axis=0) * capacity_factor * 8760
    opex_total_per_kwh = opex_per_hr_df.divide(opex_per_hr_df.index, axis=0)
    full_elec_effic_factsheets_all = pd.read_csv(root_dir + file_elec_effic, index_col=0, dtype='float64',
                                                 thousands=',')
    full_therm_effic_factsheets_all = pd.read_csv(root_dir + file_therm_effic, index_col=0, dtype='float64',
                                                  thousands=',')
    size_class_data_all = {}
    size_class_avg_pwr = {}
    capex_class = {}
    capex_sizes = {}
    opex_class = {}
    elec_effic_full_class = {}
    therm_effic_full_class = {}
    elec_effic_half_class = {}
    therm_effic_half_class = {}
    hre_full_class = {}
    hre_half_class = {}
    for p, pm in enumerate(full_elec_effic_factsheets_all.columns):
        size_class_avg_pwr[pm] = []
        capex_class[pm] = []
        capex_sizes[pm] = []
        opex_class[pm] = []
        elec_effic_full_class[pm] = []
        therm_effic_full_class[pm] = []
        hre_full_class[pm] = []
        elec_effic_half_class[pm] = []
        therm_effic_half_class[pm] = []
        hre_half_class[pm] = []
        sizes_all = capex_per_kw_df[pm].dropna().index.values
        capex_all = capex_per_kw_df[pm].dropna()
        opex_all = opex_total_per_kwh[pm].dropna().values
        elec_effic_all = full_elec_effic_factsheets_all[pm].dropna().values
        therm_effic_all = full_therm_effic_factsheets_all[pm].dropna().values
        for i, sc in enumerate(class_bounds[pm]):
            size_class_avg_pwr[pm].append(np.mean(class_bounds[pm][i]))
            #capex_class[pm].append(np.mean(capex_all[(sizes_all >= sc[0]) & (sizes_all <= sc[1])]))
            capex_class[pm].append([capex_all[sc[0]], capex_all[sc[1]]])
            capex_sizes[pm].append([sc[0], sc[1]])
            opex_class[pm].append(np.mean(opex_all[(sizes_all >= sc[0]) & (sizes_all <= sc[1])]))
            elec_effic_full_class[pm].append(np.mean(elec_effic_all[(sizes_all >= sc[0]) & (sizes_all <= sc[1])]))
            therm_effic_full_class[pm].append(np.mean(therm_effic_all[(sizes_all >= sc[0]) & (sizes_all <= sc[1])]))
            hre_full_class[pm].append(therm_effic_full_class[pm][i] / (1 - elec_effic_full_class[pm][i]))
            elec_effic_half_class[pm].append(elec_effic_full_class[pm][i] * elec_effic_half_frac[p])
            hre_half_class[pm].append(hre_full_class[pm][i] * hre_half_frac[p])
            therm_effic_half_class[pm].append((1 - elec_effic_half_class[pm][i]) * hre_half_class[pm][i])
        # Build a dictionary of all data, grouped first by prime mover type, then by size class
        # TODO I'm putting full load efficiencies into half load efficiencies to keep constant efficieny
        size_class_data_all[pm] = {'installed_cost_us_dollars_per_kw': capex_class[pm],
                                   'tech_size_for_cost_curve': capex_sizes[pm],
                                   'om_cost_us_dollars_per_kw': [0] * len(class_bounds[pm]),
                                   'om_cost_us_dollars_per_kwh': opex_class[pm],
                                   'om_cost_us_dollars_per_hr_per_kw_rated': [0] * len(class_bounds[pm]),
                                   'elec_effic_full_load': elec_effic_full_class[pm],
                                   'elec_effic_half_load': elec_effic_full_class[pm],
                                   'thermal_effic_full_load': therm_effic_full_class[pm],
                                   'thermal_effic_half_load': therm_effic_full_class[pm],
                                   'min_allowable_kw': [class_bounds[pm][sc][0] * min_allow_frac[p] for sc in range(len(class_bounds[pm]))]}

    return size_class_data_all

processed_data = create_chp_prime_mover_defaults(class_bounds, capacity_factor, elec_effic_half_frac, hre_half_frac)