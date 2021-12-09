# -*- coding: utf-8 -*-
"""
Created on Wed Dec  8 18:04:02 2021

@author: halloranl
"""
import os
os.chdir("../")
print("Current Working Directory: " , os.getcwd())

import hydrogeosines as hgs
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

#%%
valposchiavo = hgs.Site('Valposchiavo', geoloc=[9.99645, 46.32246, 2302])  # LV03+: 2'796'960.102, 1'133'328.362, z unknown, thus estimated
#%%
valposchiavo.import_csv('C:/SYNC/Sync/PYTHON/HydroGeoSines/lh/Valposchiavo_KB4_cut.csv', 
                        input_category=['GW','GW'],
                        utc_offset = 0,
                        unit=['m', 'm'])
                        #loc_names = ['P1','T1','P2','T2','Bat',''],
                        #how="add", check_duplicates=True)
#%%
valposchiavo.add_ET()
#%%
process = hgs.Processing(fowlers)
fft_results  = process.fft(update=True)