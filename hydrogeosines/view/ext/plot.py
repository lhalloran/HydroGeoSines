# -*- coding: utf-8 -*-
"""
Created on Wed Sep 23 16:13:00 2020

@author: Daniel
"""

import pandas as pd
import numpy as np
import pytz
import matplotlib.pyplot as plt
import seaborn as sns
from ...models import const

class Plot(object):
    #add attributes specific to Visualize here

    def __init__(self, *args, **kwargs):
        pass
        #add attributes specific to Load here
        #self.attribute = variable
    
    #%%
    @staticmethod
    def plot_BE_time(site, loc, results, data, info=None):
        pass
    
    #%%
    @staticmethod
    def plot_BE_freq(site, loc, results, data, info=None):
        pass
    
    #%%
    @staticmethod
    def plot_HALS(site, loc, results, data, info=None, folder=None, **kwargs):
        print("Plotting location: {:s}".format(loc[0]))
        if 'figsize' in kwargs:
            fig, ax = plt.subplots(figsize=kwargs['figsize'])
        else:
            fig, ax = plt.subplots()
            
        for x, y, z in zip(results["phs"], results["amp"], results["component"]):
            ax.scatter(x, y, s=10, label=z)
            
        ax.set_xlabel("Phase [rad]")
        unit = '?'
        if 'unit' in info:
            unit = info['unit']
            
        ax.set_ylabel("Amplitude [" + unit + "]")
        ax.set_title(info['site'] + ': ' + loc[0] + ' (' + loc[2] + ', ' + loc[1] + ')')
        ax.set_xlim([-np.pi, np.pi])
        ax.legend()
        if isinstance(folder, str):
            print(">> Writing files to folder: {}".format(folder))
            filename = folder + '/' + site + "_" + loc[0] + '_(' + loc[1] + ')'
            plt.savefig(filename + '_HALS.png', dpi=200, bbox_inches='tight')
            
        return fig
    
    #%%
    @staticmethod
    def plot_FFT(site, loc, results, data, info=None, folder=None, **kwargs):
        print("Plotting location: {:s}".format(loc[0]))
        if 'figsize' in kwargs:
            fig, ax = plt.subplots(figsize=kwargs['figsize'])
        else:
            fig, ax = plt.subplots()
            
        ax.plot(results["freq"], results["amp"])
        
        # if loc[2] in ('GW', 'ET'):
        #     components = const.const['_etfqs']
        # else:
        #     components = const.const['_atfqs']
            
        # for comp, freq in components.items():
        #     idx1 = np.argmin(np.abs(freq - results["freq"]))
        #     idx2 = np.argmax(results["amp"][idx1-3:idx1+3])
        #     ax.plot(results["freq"][idx1-3+idx2], results["amp"][idx1-3+idx2], '.r')
        
        ax.set_xlabel("Frequency [cpd]")
        unit = '?'
        if 'unit' in info:
            unit = info['unit']
        ax.set_ylabel("Amplitude [$" + unit.replace('**', '^') + "$]")
        ax.set_title(info['site'] + ': ' + loc[0] + ' (' + loc[2] + ', ' + loc[1] + ')')
        
        if 'xlim' in kwargs:
            ax.set_xlim(kwargs['xlim'])
        else:
            ax.set_xlim([.5, 2.5])
            
        if isinstance(folder, str):
            print(">> Writing files to folder: {}".format(folder))
            filename = folder + '/' + site + "_" + loc[0] + '_(' + loc[1] + ')'
            plt.savefig(filename + '_FFT.png', dpi=200, bbox_inches='tight')
        
        return fig
    
    #%%
    @staticmethod
    def plot_GW_correct(site, loc, results, data, info=None, folder=None, **kwargs):
        print("Plotting location: {:s}".format(loc[0]))
        if 'utc_offset' in info:
            datetime = data.index.tz_convert(tz=pytz.FixedOffset(int(60*info['utc_offset']))).tz_localize(None)
            utc_offset = info['utc_offset']
        else:
            datetime = data.index.tz_localize(None)
            utc_offset = 0
        unit = '?'
        if 'unit' in info:
            unit = info['unit']
        
        # plot the correted heads
        if 'figsize' in kwargs:
            fig1, ax = plt.subplots(figsize=kwargs['figsize'])
        else:
            fig1, ax = plt.subplots()
            
        ax.plot(datetime, data.GW, c=[0.7,0.7,0.7], lw=0.5, label='Measured')
        ax.plot(datetime, results['WLc'], c='k', lw=0.5, label='Corrected')
        ax.set_xlim([datetime[0], datetime[-1]])
        ax.set_title(info['site'] + ': ' + loc[0] + ' (' + loc[1] + ') ')        
        ax.set_ylabel("Head [" + unit + "]")
        ax.set_xlabel('Datetime [UTC{:+.2f}]'.format(utc_offset))
        ax.legend()
            
        # and the response functions
        if 'figsize' in kwargs:
            fig2, ax = plt.subplots(figsize=kwargs['figsize'])
        else:
            fig2, ax = plt.subplots()
        ax1 = ax.twinx()
        
        #l1, = ax1.plot(results['brf']['lag'], results['brf']['irc'], ls='None', marker='.', ms=5, c=[.6,.6,.6], label='IRC')
        l1 = ax1.scatter(results['brf']['lag'], results['brf']['irc'], c='k', s=5, label='IRC')
        l2, = ax.plot(results['brf']['lag'], results['brf']['brf'], lw=1, c='k', label='BRF')
        
        ax.set_xlabel('Lag time [hours]')
        
        ax.set_title(info['site'] + ': ' + loc[0] + ' (' + loc[1] + ') ')

        ax.set_ylabel("BRF [-]")
        ax.set_ylim([-0.05, 1.1])
        ax1.set_ylabel("IRC [-]")
        
        ax.legend(handles=[l1,l2], loc='best')
        
        # fix date format issues
        fig1.autofmt_xdate()
        
        if isinstance(folder, str):
            filename = folder + '/' + site + "_" + loc[0] + '_(' + loc[1] + ')'
            
            print(">> Writing files to folder: {}".format(folder))
            
            fig1.savefig(filename + '_GW_correct.png', dpi=200, bbox_inches='tight')
            fig2.savefig(filename + '_GW_correct_BRF.png', dpi=200, bbox_inches='tight')
        
        return fig1, fig2
    