"""parametric analysis step

sets up the model to run the ranges defined
only set up for hot water tank capacity and heat pump
"""

import os
import pandas as pd
import shutil


class Para(object):

    def __init__(self, name):

        # read in set of parameters from input
        file1 = os.path.join(
            os.path.dirname(__file__), "..", "inputs",
            name[:-5], "parametric_analysis.pkl")
        pa = pd.read_pickle(file1)

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

        # make folders for each set of parameters
        folder = os.path.join(
            os.path.dirname(__file__), "..", "inputs",
            name[:-5])
        self.folder = folder
        for i in range(len(folder_name)):
            path = os.path.join(folder, folder_name[i])
            if os.path.isdir(path) is False:
                os.mkdir(path)
            elif os.path.isdir(path) is True:
                shutil.rmtree(path)
                os.mkdir(path)

            # make outputs folder for each set of parameters
            path = os.path.join(
                os.path.dirname(__file__), "..", "outputs",
                name[:-5], folder_name[i])
            if os.path.isdir(path) is False:
                os.mkdir(path)
            elif os.path.isdir(path) is True:
                shutil.rmtree(path)
                os.mkdir(path)

    def create_pickles(self):

        # copy pickles to new folder
        for i in range(len(self.folder_name)):
            src = self.folder
            dest = os.path.join(self.folder, self.folder_name[i])
            src_files = os.listdir(src)
            for file_name in src_files:
                full_file_name = os.path.join(src, file_name)
                if os.path.isfile(full_file_name):
                    shutil.copy(full_file_name, dest)

        # create new set of pickles for each combo
        for i in range(len(self.folder_name)):
            # read heat pump pickle for changing the basics capacity
            file1 = os.path.join(
                self.folder, "hp_basics.pkl")
            hp_basics = pd.read_pickle(file1)
            # original capacity input
            capacity = hp_basics['capacity'][0]
            # modify
            hp_basics['capacity'][0] = self.combos[i][0]
            # save
            file2 = os.path.join(
                self.folder, self.folder_name[i], "hp_basics.pkl")
            hp_basics.to_pickle(file2)

            # read heat pump pickle for changing the st reg duties
            file1 = os.path.join(
                self.folder, 'regression1.pkl')
            reg1 = pd.read_pickle(file1)
            # modify
            if capacity == 0:
                ratio = 0
            else:
                ratio = round(float(self.combos[i][0]) / float(capacity), 2)
            reg1['duty'] = reg1['duty'] * ratio
            # save
            file2 = os.path.join(
                self.folder, self.folder_name[i], 'regression1.pkl')
            reg1.to_pickle(file2)

            # read heat pump pickle for changing the st reg duties
            file1 = os.path.join(
                self.folder, 'regression2.pkl')
            reg1 = pd.read_pickle(file1)
            # modify
            reg1['duty'] = reg1['duty'] * ratio
            # save
            file2 = os.path.join(
                self.folder, self.folder_name[i], 'regression2.pkl')
            reg1.to_pickle(file2)

            # read heat pump pickle for changing the st reg duties
            file1 = os.path.join(
                self.folder, 'regression3.pkl')
            reg1 = pd.read_pickle(file1)
            # modify
            reg1['duty'] = reg1['duty'] * ratio
            # save
            file2 = os.path.join(
                self.folder, self.folder_name[i], 'regression3.pkl')
            reg1.to_pickle(file2)

            # read heat pump pickle for changing the st reg duties
            file1 = os.path.join(
                self.folder, 'regression4.pkl')
            reg1 = pd.read_pickle(file1)
            # modify
            reg1['duty'] = reg1['duty'] * ratio
            # save
            file2 = os.path.join(
                self.folder, self.folder_name[i], 'regression4.pkl')
            reg1.to_pickle(file2)

            # read ts pickle
            file1 = os.path.join(
                self.folder, "thermal_storage.pkl")
            ts = pd.read_pickle(file1)
            # modify
            ts['capacity'][0] = self.combos[i][1]
            # save
            file2 = os.path.join(
                self.folder, self.folder_name[i], "thermal_storage.pkl")
            ts.to_pickle(file2)
