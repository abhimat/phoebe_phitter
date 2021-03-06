#!/usr/bin/env python

# Stellar Params Plotter
# ---
# Abhimat Gautam

import numpy as np

from astropy import units as u
from astropy import constants as const
from astropy.table import Table, vstack

from emcee import backends

from phoebe_phitter import isoc_interp

import os
import cPickle as pickle
from tqdm import tqdm

isoc_age = 10e9
isoc_ext = 2.63
isoc_dist = 7.971e3
isoc_phase = 'RGB'
isoc_met = 0.0
isoc_atm_func = 'phoenix'

# Read in data
trial_num = 1

chains_file = '../chains/chains_try{0}.h5'.format(trial_num)
reader = backends.HDFBackend(chains_file, read_only=True)

samples = reader.get_chain()
(num_steps, num_chains, num_params) = samples.shape
samples = reader.get_chain(flat=True)

print("Number of Steps: {0}".format(num_steps))
print("Number of Chains: {0}".format(num_chains))
print("Number of Parameters: {0}".format(num_params))

log_prob_samples = reader.get_log_prob(flat=True)
log_prior_samples = reader.get_blobs(flat=True)


# Check if any rows can be ignored that have been calculated already
rows_ignore = 0

## If the data file already exists, start reading for new data
if os.path.exists('stellar_params.h5'):
    import h5py
    f = h5py.File('stellar_params.h5', 'r')
    rows_ignore, = f['data'].shape
    
    prev_params_table = Table.read('stellar_params.h5', path='data')

# Read in light curve data
target_star = 'S2-36'
with open('../lc_data.pkl', 'rb') as input_pickle:
    target_binary_period = pickle.load(input_pickle)
    phase_shift_fit = pickle.load(input_pickle)
    kp_target_mags = pickle.load(input_pickle)
    kp_target_mag_errors = pickle.load(input_pickle)
    kp_target_MJDs = pickle.load(input_pickle)
    kp_phased_days = pickle.load(input_pickle)
    h_target_mags = pickle.load(input_pickle)
    h_target_mag_errors = pickle.load(input_pickle)
    h_target_MJDs = pickle.load(input_pickle)
    h_phased_days = pickle.load(input_pickle)


num_observations = len(kp_target_mags) + len(h_target_mags)
print("Number of Observations: {0}".format(num_observations))

# Samples of fitted parameters
K_ext_samps = samples[:, 0][rows_ignore:]
H_ext_mod_samps = samples[:, 1][rows_ignore:]
star1_rad_samps = samples[:, 2][rows_ignore:]
star2_rad_samps = samples[:, 3][rows_ignore:]
binary_inc_samps = samples[:, 4][rows_ignore:]
binary_per_samps = samples[:, 5][rows_ignore:]
# binary_dist_samps = samples[:, 5][rows_ignore:]
t0_samps = samples[:, 6][rows_ignore:]

log_prob_samps = log_prob_samples[rows_ignore:]

num_samples = len(K_ext_samps)

parameter_names = ['K_ext', 'H_ext_mod', 'rad_1', 'rad_2', 'inc', 'period', 't0']

# Other stellar and binary parameters to derive
## Stellar parameters, to be derived from isochrone
star1_mass_init_samps = np.empty(num_samples)
star1_mass_samps = np.empty(num_samples)
star1_lum_samps = np.empty(num_samples)
star1_teff_samps = np.empty(num_samples)
star1_logg_samps = np.empty(num_samples)
star1_mag_Kp_samps = np.empty(num_samples)
star1_mag_H_samps = np.empty(num_samples)
star1_pblum_Kp_samps = np.empty(num_samples)
star1_pblum_H_samps = np.empty(num_samples)

star2_mass_init_samps = np.empty(num_samples)
star2_mass_samps = np.empty(num_samples)
star2_lum_samps = np.empty(num_samples)
star2_teff_samps = np.empty(num_samples)
star2_logg_samps = np.empty(num_samples)
star2_mag_Kp_samps = np.empty(num_samples)
star2_mag_H_samps = np.empty(num_samples)
star2_pblum_Kp_samps = np.empty(num_samples)
star2_pblum_H_samps = np.empty(num_samples)

## Binary parameters
binary_sma_samps = np.empty(num_samples)
binary_sma_samps_solRad = np.empty(num_samples)
binary_q_samps = np.empty(num_samples)
binary_q_init_samps = np.empty(num_samples)

## Fit Characteristics
fit_chi2red_samps = np.empty(num_samples)
fit_BIC_samps = np.empty(num_samples)

# Generate PopStar isochrone
from popstar import synthetic, evolution, atmospheres, reddening
from popstar.imf import imf, multiplicity

from phoebe_phitter import isoc_interp

## Parameters for PopStar isochrone
isochrone = isoc_interp.isochrone_mist(age=isoc_age, ext=isoc_ext,
                                       dist=isoc_dist, phase=isoc_phase,
                                       met=isoc_met, use_atm_func=isoc_atm_func)


# Derive stellar and binary parameters for each sample
for cur_samp_num in tqdm(range(num_samples)):
    cur_star1_rad = star1_rad_samps[cur_samp_num]
    cur_star2_rad = star2_rad_samps[cur_samp_num]
    cur_binary_period = binary_per_samps[cur_samp_num] * u.d

    ## Stellar parameters from isochrone
    (star1_params_all, star1_params_lcfit) = isochrone.rad_interp(cur_star1_rad)
    (star2_params_all, star2_params_lcfit) = isochrone.rad_interp(cur_star2_rad)

    (cur_star1_mass_init, cur_star1_mass, cur_star1_rad, cur_star1_lum,
        cur_star1_teff, cur_star1_logg, cur_star1_mag_Kp, cur_star1_mag_H,
        cur_star1_pblum_Kp, cur_star1_pblum_H) = star1_params_all
    (cur_star2_mass_init, cur_star2_mass, cur_star2_rad, cur_star2_lum,
        cur_star2_teff, cur_star2_logg, cur_star2_mag_Kp, cur_star2_mag_H,
        cur_star2_pblum_Kp, cur_star2_pblum_H) = star2_params_all

    ## Binary parameters
    cur_binary_sma = ((cur_binary_period**2. * const.G * (cur_star1_mass + cur_star2_mass)) / (4. * np.pi**2.))**(1./3.)

    cur_binary_q = cur_star2_mass / cur_star1_mass
    cur_binary_q_init = cur_star2_mass_init / cur_star1_mass_init

    ## Store out all the values
    star1_mass_init_samps[cur_samp_num] = cur_star1_mass_init.to(u.solMass).value
    star1_mass_samps[cur_samp_num] = cur_star1_mass.to(u.solMass).value
    star1_lum_samps[cur_samp_num] = cur_star1_lum.to(u.solLum).value
    star1_teff_samps[cur_samp_num] = cur_star1_teff.to(u.K).value
    star1_logg_samps[cur_samp_num] = cur_star1_logg
    star1_mag_Kp_samps[cur_samp_num] = cur_star1_mag_Kp
    star1_mag_H_samps[cur_samp_num] = cur_star1_mag_H
    star1_pblum_Kp_samps[cur_samp_num] = cur_star1_pblum_Kp.to(u.solLum).value
    star1_pblum_H_samps[cur_samp_num] = cur_star1_pblum_H.to(u.solLum).value

    star2_mass_init_samps[cur_samp_num] = cur_star2_mass_init.to(u.solMass).value
    star2_mass_samps[cur_samp_num] = cur_star2_mass.to(u.solMass).value
    star2_lum_samps[cur_samp_num] = cur_star2_lum.to(u.solLum).value
    star2_teff_samps[cur_samp_num] = cur_star2_teff.to(u.K).value
    star2_logg_samps[cur_samp_num] = cur_star2_logg
    star2_mag_Kp_samps[cur_samp_num] = cur_star2_mag_Kp
    star2_mag_H_samps[cur_samp_num] = cur_star2_mag_H
    star2_pblum_Kp_samps[cur_samp_num] = cur_star2_pblum_Kp.to(u.solLum).value
    star2_pblum_H_samps[cur_samp_num] = cur_star2_pblum_H.to(u.solLum).value

    ## Binary parameters
    binary_sma_samps[cur_samp_num] = cur_binary_sma.to(u.AU).value
    binary_sma_samps_solRad[cur_samp_num] = cur_binary_sma.to(u.solRad).value
    binary_q_samps[cur_samp_num] = cur_binary_q
    binary_q_init_samps[cur_samp_num] = cur_binary_q_init
    
    ## Fit Characteristics
    ### Reduced chi squared
    fit_chi2red_samps[cur_samp_num] = (log_prob_samps[cur_samp_num] * -2.) / (num_observations - num_params)
    
    ### Bayesian Information Criterion
    fit_BIC_samps[cur_samp_num] = (num_params * np.log(num_observations * 1.)) - (2. * log_prob_samps[cur_samp_num])
    



# Make parameter table
params_table = Table([K_ext_samps, H_ext_mod_samps,
                      star1_rad_samps*u.solRad, star2_rad_samps*u.solRad,
                      binary_inc_samps*u.deg, binary_per_samps*u.d,
                      t0_samps,
                      star1_mass_init_samps*u.solMass, star1_mass_samps*u.solMass,
                      star1_lum_samps*u.solLum, star1_teff_samps*u.K, star1_logg_samps,
                      star1_mag_Kp_samps, star1_mag_H_samps,
                      star1_pblum_Kp_samps*u.solLum, star1_pblum_H_samps*u.solLum,
                      star2_mass_init_samps*u.solMass, star2_mass_samps*u.solMass,
                      star2_lum_samps*u.solLum, star2_teff_samps*u.K, star2_logg_samps,
                      star2_mag_Kp_samps, star2_mag_H_samps,
                      star2_pblum_Kp_samps*u.solLum, star2_pblum_H_samps*u.solLum,
                      binary_sma_samps*u.AU, binary_q_samps, binary_q_init_samps,
                      log_prob_samps, fit_chi2red_samps, fit_BIC_samps],
                     names=('K_ext', 'H_ext_mod',
                            'star1_rad', 'star2_rad',
                            'binary_inc', 'binary_per',
                            't0',
                            'star1_mass_init', 'star1_mass',
                            'star1_lum', 'star1_teff', 'star1_logg',
                            'star1_mag_Kp', 'star1_mag_H',
                            'star1_pblum_Kp', 'star1_pblum_H',
                            'star2_mass_init', 'star2_mass',
                            'star2_lum', 'star2_teff', 'star2_logg',
                            'star2_mag_Kp', 'star2_mag_H',
                            'star2_pblum_Kp', 'star2_pblum_H',
                            'binary_sma', 'binary_q', 'binary_q_init',
                            'log_prob', 'fit_chi2red', 'fit_BIC'))


if os.path.exists('stellar_params.h5'):
    params_table = vstack([prev_params_table, params_table])

    params_table.write('stellar_params.h5', path='data',
                       serialize_meta=True, compression=True,
                       overwrite=True)
else:
    params_table.write('stellar_params.h5', path='data',
                       serialize_meta=True, compression=True)