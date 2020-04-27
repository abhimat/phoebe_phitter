#!/usr/bin/env python

# Model Uncertainties at Observation Times Calculator
# ---
# Abhimat Gautam


# Imports
import numpy as np

from phoebe_phitter import mcmc_fit

from multiprocessing import Pool
import parmap
parallel_cores = 7

import cPickle as pickle
import time

trial_num = 1
burn_ignore_len = 500
num_plot_samples = 100


# Isochrone parameters
isoc_age = 12.8e9
isoc_ext = 2.63
isoc_dist = 7.971e3
isoc_phase = 'RGB'
isoc_met = 0.0

# Read in observation data
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

# Set up MCMC fitting object
## We'll be regenerating model light curves using this MCMC object

mcmc_fit_obj = mcmc_fit.mcmc_fitter_rad_interp()

## Make isochrone that will be interpolated
mcmc_fit_obj.make_isochrone(isoc_age, isoc_ext, isoc_dist, isoc_phase,
                            isoc_met, use_atm_func='phoenix')

## Set observation times used during fitting (in MJDs)
mcmc_fit_obj.set_observation_times(kp_target_MJDs, h_target_MJDs)

## Set observation mags, to compare with model mags
mcmc_fit_obj.set_observation_mags(
    kp_target_mags, kp_target_mag_errors,
    h_target_mags, h_target_mag_errors)

## Set number of triangles to use in model mesh
mcmc_fit_obj.set_model_numTriangles(early_iters_num_triangles)

## Set to use blackbody atmosphere
mcmc_fit_obj.set_model_use_blackbody_atm(True)

## Set to model H extinction modifier
mcmc_fit_obj.set_model_H_ext_mod(True)

## Set to not model eccentricity
mcmc_fit_obj.set_model_eccentricity(False)

## Set to model distance
mcmc_fit_obj.set_model_distance(False)
mcmc_fit_obj.default_dist = 7.971e3

# Set prior bounds
mcmc_fit_obj.set_Kp_ext_prior_bounds(1.0, 4.0)
mcmc_fit_obj.set_H_ext_mod_prior_bounds(-2.0, 2.0)

mcmc_fit_obj.set_period_prior_bounds(73.0, 85.0)
mcmc_fit_obj.set_dist_prior_bounds(4000., 12000.)
mcmc_fit_obj.set_t0_prior_bounds(init_t0_t - (init_binary_period_t * 0.5),
                                 init_t0_t + (init_binary_period_t * 0.5))


# Extract random sets of parameters from the chains

# test_theta = (init_Kp_ext_t, init_H_ext_mod_t,
#               init_star1_rad_t, init_star2_rad_t,
#               init_binary_inc_t, init_binary_period_t,
#               init_t0_t)

## Chains file name
filename = '../chains/chains_try{0}.h5'.format(trial_num)

## Read in sample
import emcee
reader = emcee.backends.HDFBackend(filename, read_only=True)

samples = reader.get_chain()
(num_steps, num_chains, num_params) = samples.shape
samples = reader.get_chain(flat=True)

## Random indices for calculation
total_samples = (num_steps - burn_ignore_len) * num_chains

rng = np.random.default_rng()
plot_indices = rng.choice(total_samples, size=num_plot_samples, replace=False)

## Samples at random indices
samples = samples[burn_ignore_len * num_chains:,:]

plot_binary_params = samples[plot_indices]



# Generate binary light curves at the random parameter indices

## Function for parallelization
def binary_lc_run(run_num, binary_params):
    cur_binary_params = binary_params[run_num]
    cur_theta = (cur_binary_params[0], cur_binary_params[1],
                 cur_binary_params[2], cur_binary_params[3],
                 cur_binary_params[4], cur_binary_params[5],
                 cur_binary_params[6])
    
    (cur_model_mags_Kp, cur_model_mags_H) = mcmc_fit_obj.calculate_model_lc(cur_theta)

    return [cur_model_mags_Kp_dataTimes, cur_model_mags_H_dataTimes]


## Calculate model light curves with parallelization
start_time = time.time()
binary_lc_run_pool = Pool(processes=parallel_cores)
binary_lc_result = parmap.map(binary_lc_run,
                              range(num_plot_samples), plot_binary_params,
                              pool=binary_lc_run_pool)
end_time = time.time()

print('Number of sample binary models = {0}'.format(num_plot_samples))
print('Total binary modeling time = {0:.3f} sec'.format(end_time - start_time))

## Re-shape pool outputs into numpy arrays
model_good_trials = np.zeros(num_plot_samples)
model_obs_trials_kp = np.zeros((num_plot_samples, len(kp_target_MJDs)))
model_obs_trials_h = np.zeros((num_plot_samples, len(h_target_MJDs)))

for samp_run in range(num_plot_samples):
    [cur_model_mags_Kp, cur_model_mags_H] = binary_lc_result[samp_run]
    
    if (cur_model_mags_Kp[0] == -1.) or (cur_model_mags_H[0] == -1.):
        model_good_trials[samp_run] = 0
        continue
    else:
        model_good_trials[samp_run] = 1
        model_obs_trials_kp[samp_run] = cur_model_mags_Kp_dataTimes
        model_obs_trials_h[samp_run] = cur_model_mags_H_dataTimes



# Save out calculated values
with open('./obs_modelUnc_try{0}.pkl'.format(trial_num), 'wb') as output_pickle:
    pickle.dump(plot_indices, output_pickle)
    pickle.dump(plot_binary_params, output_pickle)
    pickle.dump(model_good_trials, output_pickle)
    pickle.dump(model_obs_trials_kp, output_pickle)
    pickle.dump(model_obs_trials_h, output_pickle)

