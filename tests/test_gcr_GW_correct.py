# -*- coding: utf-8 -*-
"""
Created on Mon Jun  7 09:30:26 2021

@author: Daniel
"""

import hydrogeosines as hgs
import numpy as np
import pandas as pd

#%%  Testing MVC principal
death_valley = hgs.Site('death valley', geoloc=[-116.471360, 36.408130, 688])
death_valley.import_csv('tests/data/death_valley/Rau_et_al_2021.csv',
                        input_category=["GW","BP"],
                        unit=["m","m","nstr"],
                        utc_offset=0,
                        how="add", check_duplicates=True)

#%% Processing
# create Instance of Processing with csiro_site
process = hgs.Processing(death_valley)

#%%
process.describe()

#%% test gw_correct
gw_correct_results  = process.GW_correct(lag_h=8, et_method='ts')

correct_output  = hgs.Output(gw_correct_results)

#%%
correct_output.export()
correct_output.plot()
