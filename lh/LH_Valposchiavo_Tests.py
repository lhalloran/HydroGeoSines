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
import seaborn as sns
sns.set_style('darkgrid')

#%% make "Site"
valposchiavo = hgs.Site('Valposchiavo', geoloc=[9.99645, 46.32246, 2302])  # LV03+: 2'796'960.102, 1'133'328.362, z unknown, thus estimated
#%%
valposchiavo.import_csv('C:/SYNC/Sync/PYTHON/HydroGeoSines/lh/Valposchiavo_KB4_cut_from20200219.csv', # must use the chopped version as baro data from 19.2.2020
                        input_category=['GW','GW'],
                        utc_offset = 0,
                        unit=['m', 'm'])
                        #loc_names = ['P1','T1','P2','T2','Bat',''],
                        #how="add", check_duplicates=True)
valposchiavo.import_csv('C:/SYNC/Sync/PYTHON/HydroGeoSines/lh/Valposchiavo_baro.csv', 
                        input_category=['BP'],
                        utc_offset = 0,
                        unit=['kPa'])
                        
#%%
valposchiavo.add_ET()
#%% resample to f_s = 1 hr
valposchiavo_resampled = valposchiavo.data.hgs.make_regular(method='piecewise_polynomial',inter_max=3600*7,spl_freq = 3600,inter_max_total = 100)
valposchiavo_resampled.hgs.spl_freq_groupby # sampling freq data...

#%% align samples
valposchiavo_aligned = valposchiavo_resampled.hgs.BP_align(inter_max = 3600) # only works if GW data with no BP overlap is not included, otherwise inf. loop
valposchiavo_aligned.hgs.check_alignment()
vp = valposchiavo_aligned.hgs.pivot

#### issue... this result should be simple to re-integrate into a "Site" object

#%% 

locs = valposchiavo_aligned['location'].unique()
nlocs = np.size(locs)

fig, ax = plt.subplots(nrows=nlocs,ncols=1,figsize=(10,8),sharex=True)
for i in np.arange(nlocs):
    locnow = locs[i]
    datanow = valposchiavo_aligned[valposchiavo_aligned['location']==locnow]
    ax[i].plot(datanow['datetime'], datanow['value'])
    ax[i].set_ylabel(locnow)

#%% testing Processing to do the same as above...
process = hgs.Processing(valposchiavo).RegularAndAligned(method = 'piecewise_polynomial', inter_max = 3600*7, spl_freq = 3600, inter_max_total = 100)

#process.BE_time(method='piecewise_polynomial',inter_max=3600*7)

#%%

fft_results  = process.fft(update=True)['fft'] # fft entry is redundant I think...
nfft_res = len(fft_results.keys())
#%%
fig, ax = plt.subplots(nrows=nfft_res,ncols=1,figsize=(10,8),sharex=True)
i=0
for key in fft_results.keys():
    print(key)
    fnow = np.array(fft_results[key][0]['freq'])
    anow = np.array(fft_results[key][0]['amp'])
    ax[i].plot(fnow,anow)
    ax[i].set_ylabel(key)
    i=i+1
ax[-1].set_xlabel('freq (/d)')
ax[0].set_xlim([0,2])

#%%  
VP_BE_time_results = process.BE_time()['be_time'] # be_time entry is redundant I think...
print(VP_BE_time_results)
#for item in VP_BE_time_results['be_time']:
#    print(item)
#fig, ax = plt.subplots(nrows=len(VP_BE_time_results.keys()),ncols=1,figsize=(10,8),sharex=True)
#i=0
for key in VP_BE_time_results.keys():
    print(key)
    print(VP_BE_time_results[key])
    #fnow = np.array(VP_BE_time_results[key][0]['freq'])
    #anow = np.array(VP_BE_time_results[key][0]['amp'])
    #ax[i].plot(fnow,anow)
    #ax[i].set_ylabel(key)
    #i=i+1

#%%

