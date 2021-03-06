# -*- coding: utf-8 -*-
"""
=============================
Elekta phantom data with LCMV
=============================
"""
# authors: Amit & Alex & Eric

from __future__ import print_function

from itertools import product

import numpy as np
import pandas as pd
import mne
from mne.parallel import parallel_func

from phantom_helpers import get_data, plot_errors, get_bench_params, get_fwd
from phantom_helpers import get_dataset, compute_error

base_path, postfix = get_dataset('aston')
# base_path, postfix = get_dataset('')

(maxfilter_options, dipole_amplitudes, dipole_indices, actual_pos,
    actual_ori, bads) = get_bench_params(base_path)

src, fwd = get_fwd(base_path)


def run(da, di, mf):
    print(('Processing : %4d nAm (dip %d) : SSS=%s'
          % (da, di, mf)).ljust(42), end='')
    epochs, evoked, cov, sphere = get_data(
        base_path, di, da, mf, bads=bads)
    # Hack to only use gradiometers
    epochs.pick_types(meg='grad')
    evoked.pick_types(meg='grad')
    # Do LCMV
    data_cov = mne.compute_covariance(epochs, tmin=0.)
    stc = mne.beamformer.lcmv(
        evoked, fwd, cov, data_cov, reg=0.01, pick_ori='max-power',
        reduce_rank=True, max_ori_out='signed')
    stc = abs(stc)
    idx_max = np.argmax(np.mean(stc.data, axis=1))
    vertno_max = stc.vertices[idx_max]
    pos = src[0]['rr'][vertno_max]
    ori = None
    amp = None
    gof = None

    actual_params = dict(actual_pos=actual_pos[di - 1],
                         actual_ori=actual_ori[di - 1],
                         actual_amp=da / 2.)
    error = compute_error(di, pos, ori, amp, **actual_params)
    error['gof'] = gof
    error['maxfilter'] = mf
    return pd.DataFrame(error, index=[0])

parallel, prun, _ = parallel_func(run, n_jobs=3)
errors = parallel([prun(da, di, mf) for mf, da, di in
                   product(maxfilter_options, dipole_amplitudes,
                           dipole_indices)])
errors = pd.concat(errors, axis=0, ignore_index=True)
errors['method'] = 'lcmv'

plot_errors(errors, 'lcmv', postfix=postfix)
