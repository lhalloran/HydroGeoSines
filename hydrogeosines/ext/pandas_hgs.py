# -*- coding: utf-8 -*-
"""
Created on Thu Nov 19 08:55:47 2020

@author: Daniel
"""

import pandas as pd 
import numpy as np

from .time import Time
from .hgs_filters import HgsFilters

from .. import utils

@pd.api.extensions.register_dataframe_accessor("hgs")
class HgsAccessor(object):
    def __init__(self, pandas_obj):
        super().__init__()
        self._validate(pandas_obj)
        self._obj   = pandas_obj
    
    @staticmethod
    def _validate(obj):
        #TODO: verify that datetime localization exists (absolut, non-naive datetime)
        #TODO: varify that only valid data categories exist!
        # verify there is a column datetime, location, category, unit and value        
        if not set(["datetime","category","location","part","unit","value"]).issubset(obj.columns):
            raise AttributeError("Must have 'datetime','category','location', 'part', 'unit' and 'value' columns.")               
    
    #%%
    ## setting datetime as a property and extending it by the Time methods
    @property
    def dt(self):
        return Time(self._obj.datetime)
    
    #%%
    ## setting filters as a property and extending it by the HgsFilters methods
    @property
    def filters(self):
        return HgsFilters(self._obj)
    
    #%%
    @property
    def pivot(self):
        return self._obj.pivot_table(index=self.dt._obj, columns=self.filters.obj_col, values="value")    
      
    #%%
    @property
    def spl_freq_groupby(self):
        # returns most ofen found sampling frequency grouped by object-dtype columns, in seconds
        df = self._obj[self._obj.value.notnull()]
        df = df.groupby(self.filters.obj_col, dropna=False)["datetime"].agg(lambda x: (x.diff(periods=1).dt.seconds).mode())
        #df = df.index.droplevel(3) # remove the zero index entry
        return df
      
    #%%
    @property
    def check_duplicates(self):
        # search for duplicates (in rows)
        if any(self._obj.duplicated(subset=None, keep='first')):                
            print("Duplicate entries were detected and deleted.")            
            return self._obj.drop_duplicates(subset=None, keep='first', ignore_index=True)
        else:
            print("No duplicate entries were found.")
            return self._obj
    
    #%%
    def check_alignment(self, cat:str="BP", silent:bool=False):
        df = self._obj
        # mask possible other categories values
        df = df[df["category"].isin(["GW", cat])]
        df = df.hgs.pivot
        
        # check if any BP entry is null and if for any row all the GW entries are null        
        if (df[cat].isnull().any().bool() == False) and (df["GW"].isnull().all().any() == False):
            if silent == False:
                print("The groundwater (GW) and  {} data is aligned. There is exactly one {} for every GW entry!".format(cat,cat))
            return True
        else:
            if silent == False:
                print("Your groundwater data is NOT aligned with {}. Please consider using the 'make_regular' and 'bp_align' methods!".format(cat))  
            return False
    
    #%%
    @staticmethod
    def unit_converter_vec(df, unit_dict:dict):  
        # adjust values based on a unit conversion factor dictionary
        return df.value*np.vectorize(unit_dict.__getitem__)(df.unit.str.lower())
    
    #%%
    # ????
    def get_loc_unit(self, cat='GW'):  
        unit = self._obj.loc[(self._obj['category'] == cat), 'unit']
        if unit.empty:
            return False
        else:
            return unit.iloc[0]
    
    #%%
    def pucf_converter_vec(self, unit_dict:dict): # using vectorization        
        # convert pressure units for GW and BP into SI unit meter    
        df = self._obj
        idx     = df.category.isin(["GW","BP"]) & (df.unit != "m")
        if len(df[idx]) > 0:
            print("Convert pressure to SI unit meter.")
            df.loc[idx, "value"] = self.unit_converter_vec(df[idx], unit_dict) 
            df.loc[:, "unit"]    = np.where(idx, "m", df.unit) 
        return df
    
    #%%
    def pucf_converter(self, row): # loop based
        # convert pressure units for GW and BP into SI unit meter
        if row["category"] in ("GW", "BP") and row["unit"] != "m":
            return row["value"] * self.const['_pucf'][row["unit"].lower()], "m"
        else:
            return row["value"], "m"
    
    #%%
    def upsample(self, method = "time"):
        out = self._obj.set_index("datetime")
        out = out.interpolate(method=method).reset_index(drop=False)[self._obj.columns]
        return out      
    
    #%%
    def resample(self, freq,origin:str = "start_day"):
        # resamples by group and by a given frequency in "seconds".
        # should be used on the (calculated) median frequency of the datetime
        out = self._obj.groupby(self.filters.obj_col).resample(str(int(freq))+"S", on="datetime", origin=origin).mean()
        # reorganize index and column structure to match original hgs dataframe
        out = out.reset_index()[self._obj.columns]
        return out
    
    #%%
    def resample_by_group(self, freq_groupby, origin:str= "start"):
        #TODO: write validation logic for freq_groupby. It must be same length as number of groups, e.g. len(cat*loc*unit)
        # resample by median for each location and category individually
        out = []
        for i in range(len(freq_groupby)):
            # create mask for valid index
            a = self._obj.loc[:,self.filters.obj_col].isin(freq_groupby.index[i]).all(axis=1)
            # resample       
            print(self.filters.obj_col)
            temp = self._obj[a].groupby(self.filters.obj_col).resample(str(int(freq_groupby[i]))+"S", on="datetime", origin=origin).mean()
            print(temp)
            temp = temp.reset_index()
            out.append(temp) 
        out = pd.concat(out, axis=0, ignore_index=True, join="inner", verify_integrity=True) 
        # reorganize index and column structure to match original hgs dataframe
        out = out.reset_index()[self._obj.columns]
        return out  
    
    #%%
    def location_splitter(self, part_size:int = 30, dt_threshold:int = 3600):
        """
        Split dataframe into multiple parts using a maximum timedelta threshold. 
    
        Parameters
        ----------
        df : pd.DataFrame
            HGS DataFrame with "location" column.
        part_size : int, optional
            Minimum number of entries for location data subset. The default is 30.
        dt_threshold : int, optional
            Maximum timedelta threshold. The default is 3600.
    
        Returns
        -------
        df : pd.DataFrame
            Original dataframe with an additional column for location "parts".
    
        """
        diff = self._obj.datetime.diff()
        # find gaps larger than td_threshold
        mask = diff.dt.total_seconds() >= dt_threshold
        idx = diff[mask].index # get start index of data block
        # split index into blocks
        blocks = np.split(self._obj.index, idx, axis=0)
        # apply minimum blocksize
        blocks = [block for block in blocks if len(block) > part_size]
        if len(blocks) == 0:
            print("Not enough data for '{}' to ensure minimum part size!".format(self._obj.location.unique()[0]))
            return pd.DataFrame(columns=self._obj.columns)
        else:    
            # list of new data frames
            list_df = [self._obj.iloc[i,:].copy() for i in blocks]
            # add new column for location "parts"
            for i, val in enumerate(list_df):
                if "part" not in val.columns: 
                    # use character string format
                    val.insert(3,"part",str(i+1))    
                else:
                    val.loc[val["part"] != np.nan,"part"] = str(i+1)
            # concat df back with new column for "part"         
            if len(list_df) == 1:
                return list_df[0]
            else:
                return pd.concat(list_df,ignore_index=True,axis=0)
    
    #%%
    def gap_routine(group, mcf:int = 300, inter_max:int = 3600, part_min: int = 20, method: str = "backfill", inter_max_total: int= 10, split_location=True):
        """
        A method that can be passed into a groupby apply function in order to upsample all data null value gaps that are smaller then a threshold timedelta.
        And split locations into smaller parts for subsets separated by null value gaps larger then a threshold timedelta. Parts need to fullfill a minimum size requirement. 
    
        Parameters
        ----------
        group : pd.DataFrame
            HGS DataFrame with "location" column.
        mcf : int, optional
            Most common frequency. The default is 300.
        inter_max : int, optional
            Maximum timedelta in seconds to be interpolated. The default is 3600.
        part_min : int, optional
            Minimum size of location part as timedelta in days. The default is 20.
        method : str, optional
            Interpolation method for upsampling to inter_max. The default is "backfill".
        inter_max_total : int, optional
            Maximum percentage threshold of values to be interpolated. The default is 10.
        split_location : TYPE, optional
            Activate location splitting for large gaps. The default is True.
    
        Raises
        ------
        Exception
            DESCRIPTION.
        exception
            DESCRIPTION.
    
        Returns
        -------
        group : pd.Dataframe
            HGS DataFrame with all gaps due to null values being removed.
    
        """
        #print(group.name)
        # get mcf for group
        if isinstance(mcf,int):
            mcf_group = mcf
        elif isinstance(mcf,pd.Series):    
            mcf_group = mcf.xs(group.name)
        else:
            raise Exception("Error: Wrong format of mcf variable in gap_routine!")
        # maximum number of gaps    
        maxgap = inter_max/mcf_group
        # create mask for gaps
        s = group["value"]
        mask, counter = utils.gap_mask(s,maxgap)
        # use count of masked values to check ratio
        if counter/len(s)*100 <= inter_max_total:
            if "part" in group.columns:
                print("{:.2f} % of the '{}' data at '{}_{}' was interpolated due to gaps < {}s!".format((counter/len(s)*100), group.name[0], group.name[1], group.name[2],inter_max))
            else:    
                print("{:.2f} % of the '{}' data at '{}' was interpolated due to gaps < {}s!".format((counter/len(s)*100), group.name[0], group.name[1],inter_max))
        else:
            raise Exception("Error: Interpolation limit of {:.2f} % was exceeded!".format(inter_max_total))
        ## interpolate gaps smaller than maxgap
        # choose interpolation (runs on datetime index)
        group = group[mask].hgs.upsample(method=method)
        if split_location:
            ## identify large gaps, split group and reassamble
            # get minimum part_size (n_entries)
            part_size = int(part_min/(mcf_group/(60*60*24)))
            # location splitter for "part" column
            group = group.hgs.location_splitter(part_size=part_size, dt_threshold=inter_max)  
        else: 
            pass
        # check for remaining nan (should be none)
        if group.hgs.filters.is_nan:
            print("Caution: Method was not able to remove all NaN!")
        else:
            pass
        return group     
    
    #%%
    def make_regular(self, inter_max:int = 3600, part_min:int = 20, method:str = "backfill", category = "GW", spl_freq: int = None, inter_max_total: int= 10):
        """
        Get a dataframe with a regular sampling by group and no NaN.

        Parameters
        ----------
        inter_max : int, optional
            Maximum of interpolated time interval in seconds. The default is 3600.
        part_min : int, optional
            Minimum record duration in days. The default is 20.
        method : str, optional
            Interpolation method of Pandas to be used. The default is "backfill".
        category : {int, array_like}, optional
            Valid category of Site object. The default is "GW".
        spl_freq : int, optional
            preset sampling frequency for all groups. The default is None.
        inter_max_total : int, optional
            Maximum percentage threshold of values to be interpolated. The default is 10.

        Returns
        -------
        regular : TYPE
            DESCRIPTION.

        """
        # only use specified data category which is GW by default
        pos = self._obj["category"].isin(np.array(category).flatten())
        df_reg = self._obj.loc[pos,:].copy()
        # keep rest of data to reassemble original dataset
        df = self._obj.drop(df_reg.index).copy()
        # use custom sampling frequency
        if spl_freq is not None:
            # use predefined sampling frequency
            mcfs = df_reg.hgs.resample(spl_freq)
        else:
            # find most common frequency (mcf)
            spl_freq = df_reg.hgs.spl_freq_groupby
            # resample to mcf
            mcfs = df_reg.hgs.resample_by_group(spl_freq)
        
        ## check for NaN in value Column
        if mcfs.hgs.filters.is_nan:        
            ## identify small and large gaps
            # group by identifier columns of site data
            regular = mcfs.groupby(mcfs.hgs.filters.obj_col).apply(HgsAccessor.gap_routine, mcf=spl_freq, 
                                                                 inter_max = inter_max, part_min = part_min, 
                                                                 method = method, inter_max_total= inter_max_total).reset_index(drop=True)      
            # reassamble DataFrame          
            regular = pd.concat([regular,df],ignore_index=True)
            print("Data of the category '{}' is regularly sampled now!".format(category))
        
        else:
            print("There were no gaps in the data after resampling!")
            regular = pd.concat([mcfs,df],ignore_index=True)
        return regular 
    
    #%% BP_align
    def BP_align(self, inter_max:int = 3600, method: str ="backfill", part_min: int = 20, inter_max_total:int = 10):
        """
        Align barometric pressure records with groundwater head data.

        Parameters
        ----------
        inter_max : int, optional
            Maximum of interpolated time interval in seconds. The default is 3600.
        method : str, optional
            Interpolation method of Pandas to be used. The default is "backfill".
        part_min : int, optional
            Minimum record duration of the groundwater data in days. The default is 20.
        inter_max_total : int, optional
            Maximum percentage threshold of values to be interpolated. The default is 10.

        Raises
        ------
        Exception
            DESCRIPTION.

        Returns
        -------
        out : TYPE
            DESCRIPTION.

        """
        # get bp and gw categories and split from rest of the data
        df = self._obj
        bp_data= self.filters.get_bp_data  
        gw_data= self.filters.get_gw_data
        df_rest = self._obj[~self._obj["category"].isin(["GW","BP"])]
        # assign missing part label to bp_data
        if "part" in bp_data.columns: 
            bp_data["part"] = bp_data["part"].fillna("all")
        
        #TODO: Check for non-valid values, create function for this
        num = 0    
        while bp_data.hgs.filters.is_nan or df.hgs.check_alignment(silent=True) == False:
            num += 1
            print("\nStart iteration No. {} ...".format(num))      
            # make sure all bp entries are sorted by date, ignoring parts:
            bp_data = bp_data.sort_values(by=["datetime"], ascending=True).reset_index(drop=True)        
            # get GW and BP most common frequencies
            spl_freqs_gw = gw_data.hgs.spl_freq_groupby
            #spl_freqs_bp = bp_data["datetime"].diff(periods=1).dt.seconds.mode().values
            
            # lists for iteration
            bp_temp = []
            gw_temp = []
            # align BP data to each gw location separately
            for name, GW in gw_data.groupby(gw_data.hgs.filters.obj_col): 
                print("\n----- {}_{} -----".format(name[1],name[2]))
                dt_start = GW["datetime"].min()
                dt_end   = GW["datetime"].max()
                spl_freq = int(spl_freqs_gw[name]) 
                # make sure a reasonable inter_max is chosen
                if (inter_max < spl_freqs_gw.values).any():
                    raise Exception("Error: The selected parameter value of {} for 'inter_max' is too low for a sampling frequency of {} for {}.\nPlease reset!".format(inter_max,spl_freq,name))
                
                # correct for datatime offset and different sampling rate
                # if all GW entries have a matching BP, use those directly
                if (GW.datetime.isin(bp_data.datetime)).all():                
                    filter_gw = bp_data.datetime.isin(GW.datetime)
                    BP = bp_data.loc[filter_gw,:]
                else:
                    print("BP record resampled to 1 sample per {}s.".format(spl_freq))
                    BP = bp_data.hgs.resample(spl_freqs_gw[name],origin=dt_start)        
                    # filter greater than the start date and smaller than the end date
                    mask = (BP["datetime"] >= dt_start) & (BP["datetime"] <= dt_end)
                    BP = BP.loc[mask]
                    
                ## identify and upsample small gaps
                if BP.hgs.filters.is_nan:
                    print("\nProcessing BP gaps ...")
                    # interpolate small gaps in BP data, and leave out bigger gaps
                    BP = BP.groupby(BP.hgs.filters.obj_col).apply(HgsAccessor.gap_routine, mcf=spl_freq, inter_max = inter_max, 
                                              method = method, inter_max_total= inter_max_total, split_location=False).reset_index(drop=True)   
                    # resample to get gaps that are larger then max_gap
                    BP = BP.hgs.resample(spl_freq)
                    # return datetimes that can not be interpolated because gaps are too big
                    datetimes = BP.loc[np.isnan(BP["value"]),"datetime"]
                    if len(datetimes) != 0:
                        print("... record gaps between {} and {} too large for interpolation!".format(datetimes.min().strftime('%Y-%m-%d %H:%M'),datetimes.max().strftime('%Y-%m-%d %H:%M')))
                        # drop GW entries for which BP gaps are too big
                        print("\nProcessing GW gaps ...")  
                        print("... dropping GW and BP entries for which BP record gaps are too big.")
                        GW = GW[~GW.datetime.isin(datetimes)] 
                        # and also drop them from the BP data again, as there won't be any matches for this location any more
                        BP = BP[~BP.datetime.isin(datetimes)]
                        # resample GW data to most common frequency
                        GW = GW.hgs.resample(spl_freq)            
                        # identify and upsample or split gaps in gw data  
                        #GW = GW.hgs.make_regular(spl_freq=spl_freq,inter_max_total=inter_max_total,part_min=part_min,inter_max=inter_max).reset_index(drop=True)
                        GW = GW.groupby(GW.hgs.filters.obj_col).apply(HgsAccessor.gap_routine, mcf=spl_freq, inter_max = inter_max, part_min = part_min,
                                              method = method, inter_max_total= inter_max_total, split_location=True).reset_index(drop=True)                        
                else:
                    print("... all done!")
                gw_temp.append(GW)
                bp_temp.append(BP)
                
            if bp_temp:   
                bp_data = pd.concat(bp_temp, axis=0, ignore_index=True, join="inner", verify_integrity=True)
            # is there any GW data left after processing the gaps (i.e. is the DataFrame empty)?    
            if gw_temp:    
                gw_data = pd.concat(gw_temp, axis=0, ignore_index=True, join="inner", verify_integrity=True)
            else:
                print("Unfortunately, there is insufficient overlap between the BP and GW data, so they cannot be aligned. Try different minimum part_size and inter_max parameters.")
                break
            
            bp_data = bp_data.drop_duplicates(subset=None, keep='first', ignore_index=True)
            df = pd.concat([gw_data, bp_data],axis=0,ignore_index=True)
    
        out = pd.concat([gw_data, bp_data, df_rest],axis=0,ignore_index=True)  
    
        return out

    #%% hgs functions and filters that might still be useful, but need to be adjusted to the package architecture    
    """
    #%% GW properties
    @property
    def gw_dt(self):
        return self.data[self.data['category'] == 'GW']['datetime'].drop_duplicates().reset_index(drop=True)
    
    #@property
    #def gw_dtf(self):
    #    return Time.dt_num(self.gw_dt)
    
    #@property
    #def gw_dts(self):
    #    return Time.dt_str(self.gw_dt)
    
    #@property
    #def gw_spd(self):
    #    return 86400/Time.spl_period(self.gw_dt, unit='s')
    
    @property
    def is_aligned(self):
        tmp = self.data.groupby(by="datetime").count()
        idx = (tmp['location'].values == tmp['location'].values[0])
        if np.all(idx):
            return True
        else:
            return False
       
    
    @property
    # https://traces.readthedocs.io/en/master/examples.html
    def dt_regular(self):
        cols = len(self.data['location'].unique())
        grouped = self.data.groupby('location')
        rows = grouped.count().max().max()
        tdata = np.empty((rows, cols))
        tdata[:, :] = np.nan
        i = 0
        for name, group in grouped:
            rows = group.shape[0]
            tdata[:rows, i] = group.loc[:, 'dt_num'].values*24*60
            i += 1
            # print(name, group)
        
        # subtract minimum to enable better precision
        min_dt_num = np.min(tdata[0, :])
        max_dt_num = np.min(tdata[-1, :])
        tdata = tdata - min_dt_num
        print(tdata)
        # perform optimisation
        def residuals(params, tdata) :
            # sumvals = np.count_nonzero(np.isfinite(tdata))
            # print(sumvals)
            real = np.empty(())
            model = np.empty(())
            # iterate through columns
            for i in range(0, tdata.shape[1]):
                idx = np.isfinite(tdata[:, i])
                dt_num = tdata[idx, i]
                frac = np.around((dt_num - params[0]) / params[1])
                model = np.hstack((model, params[0] + frac*params[1]))
                # real
                real = np.hstack((real, dt_num))
                
            res = real - model
            print(res)
            return res

        result = leastsq(residuals, x0=(0, 5), args=(tdata))
        print(result)
        out = np.arange(result[0][0], (max_dt_num - min_dt_num)/24/60, result[0][1]/24/60)
        # print(tdata)
        return out
    
        
    #%% SOPHISTICATED DATA ALIGNMENT
    def make_congruent(self, dt_master):
        pass
    
    def regularize(self, method='interp'):
        # https://stackoverflow.com/questions/31977442/scipy-optimize-leastsq-how-to-specify-non-parameters
        # perform a fit to (start, dt) with existing data
        pass
    """
    
    #%% slicing
    # inheritance? https://stackoverflow.com/questions/25511436/python-is-is-possible-to-have-a-class-method-that-acts-on-a-slice-of-the-class