import pandas as pd
import numpy as np
import os
import copy
import json


defaults_not_size_class_dependent = {'min_kw': 0,
                                    'max_kw': 25000,
                                    'min_turn_down_pct': 0.25}


def create_steam_turbine_defaults():
    # Cost and performane data which varies based on size class
    size_class_data = process_size_class_data()

    # Input data which does not vary based on size class for each prime mover
    class_independent_data = copy.deepcopy(defaults_not_size_class_dependent)
    class_independent_data = {key: [val] * 4 for key, val in class_independent_data.items()}

    # Join class-specific data with class independent data
    defaults_all = {"steam_turbine": {**size_class_data, **class_independent_data}}

    save_directory = os.getcwd() + '/'
    json_file_name = 'steam_turbine_default_data'
    with open(save_directory + json_file_name + '.json', 'w') as fp:
        json.dump(defaults_all, fp)

    return defaults_all

# Find average values across size class for all cost and performance parameters
def process_size_class_data():
    # Data
    file_path = 'steam_turbine_defaults.csv'

    data_df = pd.read_csv(file_path, index_col=0) #, dtype='float64')

    data_dict = {}

    for i in range(len(data_df)):
        data_dict[data_df.index[i]] = []
        for j in range(len(data_df.columns)):
            data_dict[data_df.index[i]].append(data_df.iloc[i,j])

    return data_dict

processed_data = create_steam_turbine_defaults()

#Stop here to get processed_data
dummy = 10