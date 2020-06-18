"""parametric analysis step

sets up the model to run the ranges defined
only set up for hot water tank capacity and heat pump
"""

import os
import pandas as pd
import pickle
import shutil


class Para(object):

    def __init__(self, name):

        self.name = name

        # read in set of parameters from input
        file1 = os.path.join(
            os.path.dirname(__file__), "..", "inputs", name[:-5],
            "inputs.pkl")
        self.input = pd.read_pickle(file1)
        pa = self.input['parametric_analysis']

        # list set of heat pump sizes
        hp_sizes = []
        # if no step then only one size looked at
        if pa['hp_min'] == pa['hp_max']:
            hp_sizes.append(pa['hp_min'])
        else:
            for i in range(pa['hp_min'], pa['hp_max'] + pa['hp_step'], pa['hp_step']):
                hp_sizes.append(i)

        # list sizes of ts
        ts_sizes = []
        # if no step then only one size looked at
        if pa['ts_min'] == pa['ts_max']:
            ts_sizes.append(pa['ts_min'])
        else:
            for i in range(pa['ts_min'], pa['ts_max'] + pa['hp_step'], pa['ts_step']):
                ts_sizes.append(i)

        # list set of combinations
        combos = []
        for i in range(len(hp_sizes)):
            for j in range(len(ts_sizes)):
                combos.append([hp_sizes[i], ts_sizes[j]])
        self.combos = combos

        # strings for all combos to create folders for outputs and inputs
        folder_name = []
        for i in range(len(combos)):
            folder_name.append(
                'hp_' + str(combos[i][0]) + '_ts_' + str(combos[i][1]))
        self.folder_name = folder_name

        # point to folder which will contain the parametric inputs
        folder = os.path.join(
            os.path.dirname(__file__), "..", "inputs",
            name[:-5])
        self.folder = folder

        # make output folders for each combination
        for i in range(len(folder_name)):
            folder = os.path.join(
                os.path.dirname(__file__), '..', 'outputs',
                name[:-5], folder_name[i])
            if os.path.isdir(folder) is False:
                os.mkdir(folder)
            elif os.path.isdir(folder) is True:
                shutil.rmtree(folder)
                os.mkdir(folder)

    def create_pickles(self):

        # create new set of pickles for each combo
        for i in range(len(self.folder_name)):

            # read in set of parameters from input
            file1 = os.path.join(
                os.path.dirname(__file__), "..", "inputs", self.name[:-5],
                "inputs.pkl")
            self.input = pd.read_pickle(file1)

            # read heat pump pickle for changing the basics capacity
            hp_basics = self.input['hp_basics']
            # original capacity input
            capacity = hp_basics['capacity'][0]
            # modify
            hp_basics['capacity'][0] = self.combos[i][0]
            # save
            self.input['hp_basics'] = hp_basics

            # read heat pump pickle for changing the st reg duties
            reg1 = self.input['regression1']
            # modify
            if capacity == 0:
                ratio = 0
            else:
                ratio = round(float(self.combos[i][0]) / float(capacity), 2)
            reg1['duty'] = reg1['duty'] * ratio
            # save
            self.input['regression1'] = reg1

            # read heat pump pickle for changing the st reg duties
            reg2 = self.input['regression2']
            # modify
            reg2['duty'] = reg2['duty'] * ratio
            # save
            self.input['regression2'] = reg2

            # read heat pump pickle for changing the st reg duties
            reg3 = self.input['regression3']
            # modify
            reg3['duty'] = reg3['duty'] * ratio
            # save
            self.input['regression3'] = reg3

            # read heat pump pickle for changing the st reg duties
            reg4 = self.input['regression4']
            # modify
            reg4['duty'] = reg4['duty'] * ratio
            # save
            self.input['regression4'] = reg4

            # read ts pickle
            ts = self.input['thermal_storage']
            # modify
            ts['capacity'][0] = self.combos[i][1]
            # save
            self.input['thermal_storage'] = ts

            # save new pickle output
            file = os.path.join(
                self.folder, self.folder_name[i] + ".pkl")
            with open(file, 'wb') as handle:
                pickle.dump(self.input, handle, protocol=pickle.HIGHEST_PROTOCOL)
