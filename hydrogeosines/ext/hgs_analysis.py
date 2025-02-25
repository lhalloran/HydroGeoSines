# -*- coding: utf-8 -*-
"""
Created on Wed Sep 23 16:14:12 2020

@author: Daniel
"""
import os,sys
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit, least_squares
from scipy.linalg import svdvals
from scipy.stats import linregress
from scipy.signal import csd
from mpmath import ker, kei, power, sqrt

from IPython.core.display import display, HTML, Markdown

from .. import utils
from ..models import const

#%% General methods ##########################################################
def brf_total(Z):
    #print(dir(Phi))
    def brf(x, *c):
       # print(Phi)
        return Z@c
    return brf
            
def quantise(data, step):
    ''' Quantization of a signal '''
    return step*np.floor((data/step)+1/2)

#%% Static Class for TIME DOMAIN METHODS ######################################
class Time_domain(object):
    def __init__(self, GW, BP):
        self.BP = BP
        self.GW = GW
        
    @staticmethod
    def BE_average_of_ratios(X, Y):
        '''
        Calculate instantaneous barometric efficiency using the average of ratios method, a time domain solution.

        Parameters
        ----------
        X : N x 1 numpy array
            barometric pressure data,  provided as either measured values or as temporal derivatives.
        Y : N x 1 numpy array
            groundwater pressure data, provided as either measured values or as temporal derivatives.

        Returns
        -------
        scalar
            Instantaneous barometric efficiency calculated as the mean ratio of measured values or temporal derivatives.

        Notes
        -----
            ** Need to come up with a better way to avoid division by zero issues and similar
            -> maybe this works: https://stackoverflow.com/questions/26248654/how-to-return-0-with-divide-by-zero
        '''
        #with np.errstate(divide='ignore', invalid='ignore'):
        #    result = np.mean(np.divide(Y, X)[np.isfinite(np.divide(Y, X))])
        X,Y = np.round(X, 12), np.round(Y, 12)
        result = []
        for x,y in zip(X,Y):
            if x!=0.:
                result.append(y/x)
        return np.mean(result)

    @staticmethod
    def BE_median_of_ratios(X, Y):
        '''
        Calculate instantaneous barometric efficiency using the median of ratios, a time domain solution.

        Inputs:
            X - barometric pressure data,  provided as either measured values or as temporal derivatives. Should be an N x 1 numpy array.
            Y - groundwater pressure data, provided as either measured values or as temporal derivatives. Should be an N x 1 numpy array.

        Outputs:
            result - scalar. Instantaneous barometric efficiency calculated as the median ratio of measured values or temporal derivatives.
        '''
        with np.errstate(divide='ignore', invalid='ignore'):
            result = np.median(np.divide(Y, X)[np.isfinite(np.divide(Y, X))])
        return result

    @staticmethod
    def BE_linear_regression(X, Y):
        '''
        Calculate instantaneous barometric efficiency using linear regression, a time domain solution.

        Parameters
        ----------
        X : N x 1 numpy array
            barometric pressure data, provided as either measured values or as temporal derivatives.
        Y : N x 1 numpy array
            groundwater pressure data, provided as either measured values or as temporal derivatives.

        Returns
        -------
        result : scalar
            Instantaneous barometric efficiency calculated as a linear regression based on measured values or temporal derivatives.
        '''
        result = linregress(Y, X)[0]
        return result

    @staticmethod
    def BE_Clark(X, Y):
        '''
        Calculate instantaneous barometric efficiency using the Clark (1967) method, a time domain solution.

        Parameters
        ----------
        X : N x 1 numpy array
            barometric pressure data,  provided as either measured values or as temporal derivatives.
        Y : N x 1 numpy array
            groundwater pressure data, provided as either measured values or as temporal derivatives.

        Returns
        -------
        result : scalar
            Instantaneous barometric efficiency calculated using the Clark (1967) method using measured values or temporal derivatives.

        Notes
        -----
            ** Need to check that Clark's rules are implemented the right way around
        '''
        sX, sY = [0.], [0.]
        for x,y in zip(X, Y):
            sX.append(sX[-1]+abs(x))
            if x==0:
                sY.append(sY[-1])
            elif np.sign(x)==np.sign(y):
                sY.append(sY[-1]+abs(y))
            elif np.sign(x)!=np.sign(y):
                sY.append(sY[-1]-abs(y))
        result = linregress(sX, sY)[0]
        return result

    @staticmethod
    def BE_Davis_and_Rasmussen(X, Y):
        '''
        Calculate instantaneous barometric efficiency using the Davis and Rasmussen (1993) method, a time domain solution.

        Parameters
        ----------
        X : N x 1 numpy array
            barometric pressure data,  provided as either measured values or as temporal derivatives.
        Y : N x 1 numpy array
            groundwater pressure data, provided as either measured values or as temporal derivatives.

        Returns
        -------
        result : scalar
            Instantaneous barometric efficiency calculated using the Davis and Rasmussen (1993) method using measured values or temporal derivatives.
        
        Notes
        -----
            ** Work in progress - just need to marry the D&R algorithm with the automated segmenting algorithm
        '''
        cSnum    = np.zeros(1)
        cSden    = np.zeros(1)
        cSabs_dB = np.zeros(1)
        cSclk_dW = np.zeros(1)
        dB       = -np.diff(X)
        n        =  len(dB)
        j        =  len(dB[dB>0.])-len(dB[dB<0.])
        Sraw_dB  =  np.sum(dB)
        Sabs_dB  =  np.sum(np.abs(dB))
        dW       =  np.diff(Y)
        Sraw_dW  =  np.sum(dW)
        Sclk_dW  = np.zeros(1)
        for m in range(len(dW)):
            if np.sign(dW[m])==np.sign(dB[m]):
                Sclk_dW += np.abs(dW[m])
            elif np.sign(dW[m])!=np.sign(dB[m]):
                Sclk_dW -= np.abs(dW[m])
        cSnum    += (float(j)/float(n))*Sraw_dW
        cSden    += (float(j)/float(n))*Sraw_dB
        cSabs_dB += Sabs_dB
        cSclk_dW += Sclk_dW
        result = float((cSclk_dW/cSabs_dB-cSnum/cSabs_dB)/(1.-cSden/cSabs_dB))
        return result

    @staticmethod
    def BE_Rahi(X, Y):
        '''
        Calculate instantaneous barometric efficiency using the Clark (1967) method, a time domain solution.

        Parameters
        ----------
        X : N x 1 numpy array
            barometric pressure data,  provided as either measured values or as temporal derivatives.
        Y : N x 1 numpy array
            groundwater pressure data, provided as either measured values or as temporal derivatives.

        Returns
        -------
        result : scalar
            Instantaneous barometric efficiency calculated using the Rahi (2010) method using measured values or temporal derivatives.

        Notes
        -----
            ** Need to check that Rahi's rules are implemented the right way around.
        '''
        sX, sY = [0.], [0.]
        for x,y in zip(X, Y):
            if (np.sign(x)!=np.sign(y)) & (abs(y)<abs(x)):
                sX.append(sX[-1]+abs(x))
                sY.append(sY[-1]+abs(y))
            else:
                sX.append(sX[-1])
                sY.append(sY[-1])
        result = linregress(sX, sY)[0]
        return result

    @staticmethod
    def BE_Rojstaczer(X, Y, fs:float = 1.0, nperseg:int = None, noverlap:int = None):
        '''        
        Parameters
        ----------
        X : N x 1 numpy array
            barometric pressure data,  provided as either measured values or as temporal derivatives.
        Y : N x 1 numpy array
            groundwater pressure data, provided as either measured values or as temporal derivatives.
        fs : float
            The sampling frequency of interest.
        nperseg : int
            The number of data points per segment.
        noverlap : int
            The amount of overlap between data points used when calculating power and cross spectral density outputs.

        Returns
        -------
        result : scalar
            Instantaneous barometric efficiency calculated using the Quilty and Roeloffs (1991) method using measured values or temporal derivatives.

        Notes
        -----
            ** Need to check that Rojstaczer's (or Q&R's) implementation was averaged over all frequencies
        '''
        # TODO: This methods also takes fs, nperseg + noverlap as parameters. Can only be used in overarching BE_method with default values. Can fs (sampling frequency) be calculated from GW data?    
        csd_f, csd_p = csd(X, Y, fs=fs, nperseg=nperseg, noverlap=noverlap) #, scaling='density', detrend=False)
        psd_f, psd_p = csd(X, X, fs=fs, nperseg=nperseg, noverlap=noverlap) #, scaling='density', detrend=False)
        result = np.mean(np.abs(csd_p)/psd_p)
        return result
    
    @staticmethod
    def regress_deconv(tf, GW, BP, ET=None, lag_h=24, et_method=None, fqs=None):
        print('>> Applying regression deconvolution ...')
            
        if fqs is None:
            fqs = np.array(list(const.const['_etfqs'].values()))
        # check that dataset is regularly sampled
        tmp = np.diff(tf)
        if (np.around(np.min(tmp), 6) != np.around(np.max(tmp), 6)):
            raise Exception("Error: Dataset must be regularly sampled!")
        if (len(tf) != len(GW) != len(BP)):
            raise Exception("Error: All input arrays must have the same length!")

        print(">> Reference: Method by Rasmussen and Crawford (1997) [https://doi.org/10.1111/j.1745-6584.1997.tb00111.x]")

        # print(">> DEBUG: PERFORM HALS")
        t  = tf
        # samples per day
        spd = int(np.round(1/(t[1] - t[0])))
        # make the dataset relative
        dBP = np.diff(BP)
        dWL = np.diff(GW)
        # setup general parameters
        nlag = int((lag_h/24)*spd)
        n    = len(dBP)
        nn   = list(range(n))
        lags = list(range(nlag+1))
        nm = nlag+1
        # the regression matrix for barometric pressure
        V = np.zeros([n, nm])
        NP = 0
        for i in range(nm):
            j = lags[i]
            k = np.arange(n-j)
            V[j+k, i] = -dBP[k]
            
        #%% consider ET method
        if et_method == None:
            print('>> Not considering Earth tide influences ...')
            X = np.hstack([V])
            
        # HALS: harmonic least squares
        elif et_method == 'hals':
            print('>> Using harmonic least-squares to estimate Earth tide influences ...')
            # prepare ET frequencies
            f = fqs
            NP = len(f)
            omega = 2.*np.pi*f
            # the regression matrix for Earth tides
            u1 = np.zeros([n, NP])
            u2 = u1.copy()
            for i in range(NP):
                tau = omega[i]*t[nn]
                u1[:,i] = np.cos(tau)
                u2[:,i] = np.sin(tau)
            X = np.hstack([V, u1, u2])
            
        # ts: time series
        elif et_method == 'ts':
            if len(tf) != len(ET):
                raise Exception("Error: Compliant Earth tide time series must be available!")
            
            # make the dataset relative
            dET = np.diff(ET)
            lag = range(int((lag_h/24)*spd) + 1)
            print('>> Using Earth tide time series in the regression ...')
            nm = len(lag)
            W = np.zeros([n, nm])
            for i in range(nm):
                j = lag[i]
                k = np.arange(n-j)
                ### need negative?
                W[j+k, i] = dET[k]
            X = np.hstack([V, W])
            
        else:
            raise Exception("Error: Earth tide method '{}' is not recognised!".format(et_method)) 
        
        #%% perform least squares fitting
        # prepare matrix ...
        Z = np.hstack([np.ones([n,1]), X])
        # perform regression ...
        # ----------------------------------------------
        # c  = np.linalg.lstsq(Z, dWL, rcond=None)[0]
        # ----------------------------------------------            
        c = 0.5*np.ones(Z.shape[1])
        c, covar = curve_fit(brf_total(Z), t, dWL, p0=c)
        
        #%% compute the singular values
        sgl = svdvals(Z)
        # 'singular value' is important: 1 is perfect,
        # larger than 10^5 or 10^6 there's a problem
        condnum = np.max(sgl) / np.min(sgl)
        # print('>> Conditioning number: {:,.0f}'.format(condnum))
        if (condnum > 1e6):
            raise Warning('The solution is ill-conditioned (condition number {}!'.format(condnum))
            
        # ----------------------------------------------
        nc = len(c)
        # calculate the head corrections
        dWLc = np.cumsum(np.dot(X, c[1:nc]))
        # deal with the missing values
        WLc = GW - np.concatenate([[0], dWLc])
        # set the corrected heads
        WLc += (np.nanmean(GW) - np.nanmean(WLc))
        
        # adjust for mean offset
        # trend  = c[0]
        lag_t = np.linspace(0, lag_h, int((lag_h/24)*spd) + 1, endpoint=True)
        # error propagation
        brf   = c[np.arange(1, nm+1)]
        brf_covar = covar[1:nm+1,1:nm+1]
        brf_var = np.diagonal(brf_covar)
        brf_stdev = np.sqrt(brf_var)
        cbrf   = np.cumsum(brf)
        # the error propagation for summation
        cbrf_var = np.zeros(brf_var.shape)
        for i in np.arange(0, nm):
        #    if (i == 4): break
            diag = np.diagonal(brf_covar[0:i+1, 0:i+1])
            triaglow = np.tril(brf_covar[0:i+1, 0:i+1], -1)
        #    print(covatl)
            cbrf_var[i] = np.sum(diag) + 2*np.sum(triaglow)
        cbrf_stdev = np.sqrt(cbrf_var)
        params = {'brf': {'lag': lag_t, 'irc': brf, 'irc_stdev': brf_stdev, 'brf': cbrf, 'crf_stdev': cbrf_stdev}}
        
        #%% consider ET method here
        # not used
        if et_method == None:
            pass
            
        # HALS
        elif et_method == 'hals':
            k = np.arange(nm+1, NP+nm+1)
            # this is the result for the derivative WL/dt
            trf = np.array([a+(1j*b) for a,b in zip(c[k], c[NP+k])])
            names = []
            darwin_freq = list(const.const['_etfqs'].values())
            darwin_name = list(const.const['_etfqs'].keys())
            for freq in fqs:
                if freq in darwin_freq:
                    idx = darwin_freq.index(freq)
                    names.append(darwin_name[idx])
                else:
                    names.append('')
            params.update({'erf': {'freq': fqs, 'complex': trf, 'components': names}})
        
        # time series
        elif et_method== 'ts':
            erf = c[nm+1:2*nm+1]
            erf_covar = covar[nm+1:2*nm+1,nm+1:2*nm+1]
            erf_var = np.diagonal(erf_covar)
            erf_stdev = np.sqrt(erf_var)
            cerf = np.cumsum(erf)
            # the error propagation for summation
            cerf_var = np.zeros(brf_var.shape)
            for i in np.arange(0, nm):
            #    if (i == 4): break
                diag = np.diagonal(erf_covar[0:i+1, 0:i+1])
                triaglow = np.tril(erf_covar[0:i+1, 0:i+1], -1)
            #    print(covatl)
                cerf_var[i] = np.sum(diag) + 2*np.sum(triaglow)
            cerf_stdev = np.sqrt(cerf_var)
            params.update({'erf': {'lag': lag_t, 'irc': erf, 'irc_stdev': erf_stdev, 'brf': cerf, 'crf_stdev': cerf_stdev}})  
        
        # return the method results
        return WLc, params


    # https://stackoverflow.com/questions/643699/how-can-i-use-numpy-correlate-to-do-autocorrelation
    @staticmethod
    def acorr(dataset):
        """
        Calculate the autocorrelation present in an input datasets as a function of time.

        Parameters
        ----------
        dataset : numpy array
            Input dataset as a function of uniform time steps
        Returns
        -------
        results: numpy array
            Normalised autocorrelation values as functions of time lag, with delta-t equal to the sampling period
        ...
        Notes
        -------
            *** TBC ***
        """
        #results = sc.signal.correlate(dataset, dataset) # <<< scipy correlate function gives spurious results
        x = dataset
        xp = x - np.mean(x)
        f = np.fft.fft(xp)
        psd = f.conjugate()*f
        results = np.fft.ifft(psd).real[:x.size//2]/np.sum(xp**2)
        #results = f.conjugate()*f.real[:x.size//2]/numpy.var(x)/len(x) # alternate formulation for normalising results
        return results


    @staticmethod
    def xcorr(dataset1, dataset2):
        """
        Calculate the cross-correlation between two input datasets as a function of time.

        Parameters
        ----------
        dataset1 : numpy array
            Input dataset #1 as a function of uniform time steps
        dataset2 : numpy array
            Input dataset #2 as a function of uniform time steps
        Returns
        -------
        results: numpy array
            Normalised cross correlation values as functions of time lag, with delta-t equal to the sampling period
        ...
        Notes
        -------
            *** TBC ***
        """
        #results = sc.signal.correlate(dataset1, dataset2) # <<< scipy correlate function gives spurious results
        x,y = dataset1, dataset2
        xp = x-np.mean(x)
        yp = y-np.mean(y)
        fx = np.fft.fft(xp)
        fy = np.fft.fft(yp)
        csd = fx.conjugate()*fy
        results = np.fft.ifft(csd).real[:x.size//2]/np.sum(xp**2)
        #results = fx.conjugate()*fy.real[:x.size//2]/numpy.var(x)/len(x) # alternate formulation for normalising results
        return results

            
#%% Static Class for FREQUENCY DOMAIN METHODS #################################
class Freq_domain(object):
    
    #%%
    @staticmethod
    def lin_window_ovrlp(tf, data, length=3, stopper=3, n_ovrlp=3):
        """
        Windowed linear detrend function with optional window overlap
        
        Parameters
        ----------
        time : N x 1 numpy array
            Sample times.
        y : N x 1 numpy array
            Sample values.
        length : int
            Window size in days
        stopper : int 
            minimum number of samples within each window needed for detrending
        n_ovrlp : int
            number of window overlaps relative to the defined window length
            
        Returns
            -------
            y.detrend : array_like
                estimated amplitudes of the sinusoids.
        
        Notes
        -----
        A windowed linear detrend function with optional window overlap for pre-processing of non-uniformly sampled data.
        The reg_times array is extended by value of "length" in both directions to improve averaging and window overlap at boundaries. High overlap values in combination with high
        The "stopper" values will cause reducion in window numbers at time array boundaries.   
        """
        # !!! how to allow data gaps in here??
        x = np.array(tf).flatten()
        y = np.array(data).flatten()
        y_detr      = np.zeros(shape=(y.shape[0]))
        counter     = np.zeros(shape=(y.shape[0]))
        A = np.vstack([x, np.ones(len(x))]).T
        #num = 0 # counter to check how many windows are sampled   
        interval    = length/(n_ovrlp+1) # step_size interval with overlap 
        # create regular sampled array along t with step-size = interval.         
        reg_times   = np.arange(x[0]-(x[1]-x[0])-length,x[-1]+length, interval)
        # extract indices for each interval
        idx         = [np.where((x > tt-(length/2)) & (x <= tt+(length/2)))[0] for tt in reg_times]  
        # exclude samples without values (np.nan) from linear detrend
        idx         = [i[~np.isnan(y[i])] for i in idx]
        # only detrend intervals that meet the stopper criteria
        idx         = [x for x in idx if len(x) >= stopper]
        for i in idx:        
            # find linear regression line for interval
            coe = np.linalg.lstsq(A[i],y[i],rcond=None)[0]
            # and subtract off data to detrend
            detrend = y[i] - (coe[0]*x[i] + coe[1])
            # add detrended values to detrend array
            np.add.at(y_detr,i,detrend)
            # count number of detrends per sample (depends on overlap)
            np.add.at(counter,i,1)
    
        # window gaps, marked by missing detrend are set to np.nan
        counter[counter==0] = np.nan
        # create final detrend array
        y_detrend = y_detr/counter       
        if len(y_detrend[np.isnan(y_detrend)]) > 0:
            # replace nan-values assuming a mean of zero
            y_detrend[np.isnan(y_detrend)] = 0.0    
        return y_detrend
    
    #%%
    @staticmethod
    def harmonic_lsqr(tf, data, freqs):
        '''
        Inputs:
            tf      - time float. Should be an N x 1 numpy array.
            data    - estimated output. Should be an N x 1 numpy array.
            freqs   - frequencies to look for. Should be a numpy array.
        Outputs:
            alpha_est - estimated amplitudes of the sinusoids.
            phi_est - estimated phases of the sinusoids.
            error_variance - variance of the error. MSE of reconstructed signal compared to y.
            theta - parameters such that ||y - Phi*theta|| is
             minimized, where Phi is the matrix defined by
             freqs and tt that when multiplied by theta is a
             sum of sinusoids.
        '''
        print(">> Reference: Method explained in Schweizer et al. (2021) [https://doi.org/10.1007/s11004-020-09915-9]")
        # !!! find a criteria for which a dataset can be analysed
        if ((tf.max() - tf.min()) < 20):
            raise Exception("To use HALS, the duration must be >=20 days!")
        
        N = data.shape[0]
        f = np.array(freqs)*2*np.pi
        num_freqs = len(f)
        # make sure that time vectors are relative
        # avoiding additional numerical errors
        tf = tf - np.floor(tf[0])
        # assemble the matrix
        Phi = np.empty((N, 2*num_freqs + 1))
        for j in range(num_freqs):
            Phi[:,2*j] = np.cos(f[j]*tf)
            Phi[:,2*j+1] = np.sin(f[j]*tf)
        # account for any DC offsets
        Phi[:,-1] = 1
        # solve the system of linear equations
        theta, residuals, rank, singular = np.linalg.lstsq(Phi, data, rcond=None)
        # calculate the error variance
        error_variance = residuals[0]/N
        # when data is short, 'singular value' is important!
        # 1 is perfect, larger than 10^5 or 10^6 there's a problem
        condnum = np.max(singular) / np.min(singular)
        # print('>> Conditioning number: {:,.0f}'.format(condnum))
        if (condnum > 1e6):
            raise Warning('Attention: The solution is ill-conditioned!')
        # 	print(Phi)
        y_model = Phi@theta
        # the DC component
        dc_comp = theta[-1]
        # create complex coefficients
        hals_comp = theta[:-1:2]*1j + theta[1:-1:2]
        print(">> Condition number: {:,.0f}".format(condnum))
        print(">> Error variance: {:.6f}".format(error_variance))
        print(">> DC component: {:.6f}".format(dc_comp))
        result = {'freq': np.array(freqs), 'complex': hals_comp, 'error_var': error_variance, 'cond_num': condnum, 'offset': dc_comp, 'y_model': y_model}
        return result
    
    #%%
    @staticmethod
    def fft_comp(tf, data):
        if (len(tf) != len(data)):
            raise Exception("To use FFT, the times must have the same length as data!")
        if np.any(np.isnan(data)):
            raise Exception("To use FFT, the data must not have gaps!")
        if ((tf.max() - tf.min()) < 60):
            raise Exception("To use FFT, the duration must be >=60 days!")
            
        spd = 1/(tf[1] - tf[0])
        fft_N = len(tf)
        hanning = np.hanning(fft_N)
        # perform FFT
        fft_f = np.fft.fftfreq(int(fft_N), d=1/spd)[0:int(fft_N/2)]
        # FFT windowed for amplitudes
        fft_win   = np.fft.fft(hanning*data) # use signal with trend
        fft = 2*(fft_win/(fft_N/2))[0:int(fft_N/2)]
        # np.fft.fft default is a cosinus input. Thus for sinus the np.angle function returns a phase with a -np.pi shift.
        #fft_phs = fft_phs  + np.pi/2  # + np.pi/2 for a sinus signal as input
        #fft_phs = -(np.arctan(fft_win.real/fft_win.imag))
        result = {'freq': fft_f, 'complex': fft, 'dc_comp': np.abs(fft[0])}
        return result
    
    #%%
    @staticmethod
    def BE_Rau(BP_s2:complex, ET_m2:complex, ET_s2:complex, GW_m2:complex, GW_s2:complex, amp_ratio:float=1):
        """
        
        Parameters
        ----------
        BP_s2 : numpy complex
            the complex result of the S2 component obtained from a frequency analysis for barometric pressure (BP; unit in m).
        ET_m2 : numpy complex
            the complex result of the M2 component obtained from a frequency analysis for Earth tide (ET) strains (unit in nstr!).
        ET_s2 : numpy complex
            the complex result of the S2 component obtained from a frequency analysis for Earth tide (ET) strains (unit in nstr!)..
        GW_m2 : numpy complex
            the complex result of the M2 component obtained from a frequency analysis for groundwater (GW; unit in m).
        GW_s2 : numpy complex
            the complex result of the S2 component obtained from a frequency analysis for groundwater (GW; unit in m)..
        amp_ratio : float, optional
            the amplitude damping factor for the M2 and S2 frequencies. The default is 1.
        Returns
        -------
        BE : float
            barometric efficiency of the subsurface.
            
        Notes
        -------
        This calculation uses Equation 9 in Rau et al. (2020), https://doi.org/10.5194/hess-24-6033-2020
        """
        
        GW_ET_s2 = (GW_m2 / ET_m2) * ET_s2
        GW_AT_s2 = GW_s2 - GW_ET_s2
        BE = (1/amp_ratio)*np.abs(GW_AT_s2 / BP_s2)
        print(">> Reference: Method by Rau et al. (2020) [https://doi.org/10.5194/hess-24-6033-2020]")
        print(">> Barometric efficiency (BE): {:.3f} [-]".format(BE))
        
        # a phase check ...
        GW_ET_m2_dphi = np.angle(GW_m2 / ET_m2)
        if ((amp_ratio == 1) and (np.abs(GW_ET_m2_dphi) > 5)):
            raise Warning("Attention: The phase difference between GW and ET is {.1f}°. BE could be affected by amplitude damping!".format(np.degrees(GW_ET_m2_dphi)))
            
        return BE
    
    #%%
    @staticmethod
    def BE_Acworth(BP_s2:complex, ET_m2:complex, ET_s2:complex, GW_m2:complex, GW_s2:complex):
        """
        
        Parameters
        ----------
        BP_s2 : numpy complex
            the complex result of the S2 component obtained from a frequency analysis for barometric pressure (BP; unit in m).
        ET_m2 : numpy complex
            the complex result of the M2 component obtained from a frequency analysis for Earth tide (ET) strains (unit in nstr!).
        ET_s2 : numpy complex
            the complex result of the S2 component obtained from a frequency analysis for Earth tide (ET) strains (unit in nstr!)..
        GW_m2 : numpy complex
            the complex result of the M2 component obtained from a frequency analysis for groundwater (GW; unit in m).
        GW_s2 : numpy complex
            the complex result of the S2 component obtained from a frequency analysis for groundwater (GW; unit in m)..
        Returns
        -------
        BE : float
            barometric efficiency of the subsurface.
            
        Notes
        -------
        This calculation uses Equation 4 in Acworth et al. (2016), https://doi.org/10.1002/2016GL071328
        """
        # Calculate BE values
        BE = (np.abs(GW_s2)  + np.abs(ET_s2) * np.cos(np.angle(BP_s2) - np.angle(ET_s2)) * (np.abs(GW_m2) / np.abs(ET_m2))) / np.abs(BP_s2)
        print(">> Reference: Method by Acworth et al. (2016) [https://doi.org/10.1002/2016GL071328]")
        print(">> Barometric efficiency (BE): {:.3f} [-]".format(BE))
        
        # provide a user warning ...
        if (np.abs(GW_m2) > np.abs(GW_s2)):
            raise Warning("Attention: There are significant ET components present in the GW data. Please use the 'rau' method for more accurate results!")
            
        return BE
    
    #%%
    @staticmethod
    def K_Ss_Hsieh(ET_m2:complex, GW_m2:complex, scr_len:float, case_rad:float, scr_rad:float):
        # M2 frequency
        f_m2 = const.const['_etfqs']['M2']
        amp_resp = np.abs(GW_m2 / (ET_m2*1e-9))
        # ET-GW phase difference
        phase_shift = np.angle(GW_m2 / ET_m2)
        print(">> Amplitude strain response (A_str): {:,.0f} [m/nstr]".format(amp_resp))
        print(">> Phase shift (dPhi): {:.3f} [rad], {:.2f} [°]".format(phase_shift, np.degrees(phase_shift)))
        if (np.degrees(phase_shift) > 1):
            raise Exception("The phase shift is {:.2f} but must be <1 ° for the Hsieh method!".format(np.degrees(phase_shift)))
        
        #%% use the Hsieh model
        global Ker, Kei, Power, Sqrt
        Ker = np.frompyfunc(ker, 2, 1)
        Kei = np.frompyfunc(kei, 2, 1)
        Power = np.frompyfunc(power, 2, 1)
        Sqrt = np.frompyfunc(sqrt, 1, 1)

        # the horizontal flow / negative phase_shift model
        def et_hflow(K, S_s, r_w=0.1, r_c=0.1, b=2, f=f_m2):
            global Ker, Kei, Power, Sqrt
            # create numpy function from mpmath
            # https://stackoverflow.com/questions/51971328/how-to-evaluate-a-numpy-array-inside-an-mpmath-fuction
            D_h = K / S_s
            omega = 2*np.pi*f
            tmp = omega / D_h
            # prevent errors from negative square roots
            if (tmp >= 0):
                T = K*b
                sqrt_of_2 = Sqrt(2)
                alpha_w = r_w * Sqrt(tmp)
                ker_0_alpha_w = Ker(0, alpha_w)
                ker_1_alpha_w = Ker(1, alpha_w)
                kei_0_alpha_w = Kei(0, alpha_w)
                kei_1_alpha_w = Kei(1, alpha_w)
                denom = Power(ker_1_alpha_w, 2) + Power(kei_1_alpha_w, 2)
                Psi = - (ker_1_alpha_w - kei_1_alpha_w) / (sqrt_of_2 * alpha_w * denom)
                Phi = - (ker_1_alpha_w + kei_1_alpha_w) / (sqrt_of_2 * alpha_w * denom)
                E = np.float64(1 - (((omega*Power(r_c, 2))/(2*T)) * (Psi*ker_0_alpha_w + Phi*kei_0_alpha_w)))
                F = np.float64((((omega*Power(r_c,2))/(2*T)) * (Phi*ker_0_alpha_w - Psi*kei_0_alpha_w)))
                Ar = (E**2 + F**2)**(-0.5)
                dPhi = -np.arctan(F/E)
                return Ar, dPhi
            else:
                return np.Inf, np.Inf

        def fit_amp_phase(props, amp_resp, phase_shift, r_c, r_w, scr_len, freq):
            #print(props)
            K, S_s = props
            Ar, dPhi = et_hflow(K, S_s, r_c, r_w, scr_len, freq)
            res_amp = amp_resp*S_s - Ar
            res_phase = phase_shift - dPhi
            error = np.asarray([res_amp,res_phase])
            # print(error)
            return error

        print(">> Reference: Method by Hsie et al. (1987) [https://doi.org/10.1029/WR023i010p01824]")
        # least squares fitting
        fit =  least_squares(fit_amp_phase, [1e-4*24*3600, 1e-4], args=(amp_resp, phase_shift, case_rad, scr_rad, scr_len, f_m2), method='lm')
        # print(fit)

        if (fit.status > 0):
        # change units to m and s
            K = fit.x[0]/24/3600
            Ss = fit.x[1]

            print(">> Hydraulic conductivity (K): {:.2e} m/s".format(K))
            print(">> Specific storage (Ss): {:.2e} 1/m".format(Ss))
            print(">> Amplitude ratio (Ar): {:.3f} [-]".format(amp_resp*Ss))
            print(">> Residuals: Ar: {:.2e}, dPhi: {:.2e}".format(fit.fun[0], fit.fun[1]))
            results = {'A_str': amp_resp, 'dPhi': phase_shift, 'A_r': amp_resp*Ss, 'K': K, 'Ss': Ss, 'A_r_residual': fit.fun[0], 'dPhi_residual': fit.fun[1], 'screen_radius': scr_rad, 'casing_radius': case_rad, 'screen_length': scr_len}
        else:
            print(">> Attention: The solver did not converge!")
            results = {}

        return results
    
    #%%
    @staticmethod
    def K_Ss_Wang(ET_m2:complex, GW_m2:complex, scr_depth:float):
        # !!! need borehole construction parameters !!!
        
        # M2 frequency
        f_m2 = const.const['_etfqs']['M2']
        amp_resp = np.abs(GW_m2 / (ET_m2*1e-9))
        # ET-GW phase difference
        phase_shift = np.angle(GW_m2 / ET_m2)
        print(">> Amplitude strain response (A_str): {:,.0f} [m/nstr]".format(amp_resp))
        print(">> Phase shift (dPhi): {:.3f} [rad], {:.2f} [°]".format(phase_shift, np.degrees(phase_shift)))
        if (np.degrees(phase_shift) < 0):
            raise Exception("The phase shift is {:.2f} but must be >0 ° for the Wang method!".format(np.degrees(phase_shift)))
        
        # the vertical flow / positive phase_shift model
        def vflow_amp(K, S_s, z=20, f=f_m2):
            D_h = K / S_s
            omega = 2*np.pi*(f/24/3600)
            delta = np.sqrt(2*D_h/omega)
            return (np.sqrt(1 - 2*np.exp(-z/delta) * np.cos(z/delta) + np.exp((-2*z)/delta)))

        # Note: negative added in front of arctan
        def vflow_phase(K, S_s, z=20, f=f_m2):
            D_h = K / S_s
            omega = 2*np.pi*(f/24/3600)
            delta = np.sqrt(2*D_h/omega)
            return np.arctan((np.exp(-z/delta)*np.sin(z/delta))/(1-np.exp(-z/delta)*np.cos(z/delta)))

        def residuals(props, amp_ratio, phase_shift, depth, freq):
            K, S_s = props
            res_amp = amp_ratio*S_s - vflow_amp(K, S_s, depth, freq)
            res_phase = phase_shift - vflow_phase(K, S_s, depth, freq)
            error = np.asarray([res_amp, res_phase])
            # print(error)
            return error

        print(">> Reference: Method by Wang (2000) [ISBN:9780691037462]")
        # least squares fitting wang
        fit =  least_squares(residuals, [0.01, 0.01], args=(amp_resp, phase_shift, scr_depth, f_m2), bounds=((1e-20,1e-20),(0.01,0.01)), xtol=3e-16, ftol=3e-16, gtol=3e-16)

        if (fit.status > 0):
            K = fit.x[0]
            Ss = fit.x[1]
            print(">> Hydraulic conductivity (K) is: {:.3e} m/s".format(K))
            print(">> Specific storage (Ss) is: {:.3e} 1/m".format(Ss))
            print(">> Amplitude ratio (Ar): {:.3f} [-]".format(amp_resp*Ss))
            print(">> Residuals: Ar: {:.2e}, dPhi: {:.2e}".format(fit.fun[0], fit.fun[1]))
            results = {'A_str': amp_resp, 'dPhi': phase_shift, 'A_r': amp_resp*Ss, 'K': K, 'Ss': Ss, 'A_r_residual': fit.fun[0], 'dPhi_residual': fit.fun[1], 'screen_depth': scr_depth}
            
        else:
            print(">> Attention: The solver did not converge!")
            results = {}

        return results

# further methods here ...
