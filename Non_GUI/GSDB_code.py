import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt
import pywt
import pandas as pd
from scipy.interpolate import interp1d
from scipy.signal import hilbert, convolve

# resampInterp.m file
def resamp_interp(y, fs_initial, fs_final):
    recording_time = len(y)
    x = np.arange(1, recording_time + 1)
    xq = np.arange(1, recording_time + 1, fs_initial / fs_final)
    
    f = interp1d(x, y, kind='linear', bounds_error=False, fill_value="extrapolate")
    y_resamp = f(xq)
    return y_resamp

# groupfind.m file
def groupfind(L):
    L = np.asarray(L).flatten()
    temp = np.nonzero(L)[0]
    if len(temp) == 0:
        return np.empty((0, 2), dtype=int)
    
    idx = np.where(np.diff(temp) > 1)[0]
    starts = temp[np.insert(idx + 1, 0, 0)]
    ends = temp[np.append(idx, len(temp) - 1)]
    
    return np.column_stack((starts, ends))

# hilbert_envelop.m file

def hilbert_envelop(y, smooth_window=20, threshold_style=1, duration=20, gr=1):
    y = np.asarray(y).flatten()
    test = y
    analytic = hilbert(test)
    env = np.abs(analytic)

    # Smooth envelope
    env = convolve(env, np.ones(smooth_window) / smooth_window, mode='same')
    env -= np.mean(env)
    env /= np.max(env)

    # Threshold selection
    if threshold_style == 0:
        plt.figure()
        plt.plot(env)
        plt.title("Select a threshold")
        THR_SIG = float(input("Manual threshold value (0-1): "))
        plt.close()
    else:
        THR_SIG = 4 * np.mean(env)

    nois = np.mean(env) / 3
    threshold = np.mean(env)

    thres_buf = np.zeros(len(env) - duration)
    nois_buf = np.zeros(len(env) - duration)
    THR_buf = np.zeros(len(env))
    alarm = np.zeros(len(env))
    h = 1

    for i in range(len(env) - duration):
        window = env[i:i+duration]
        if np.all(window > THR_SIG):
            alarm[i] = np.max(env)
            threshold = 0.1 * np.mean(window)
            h += 1
        else:
            if np.mean(window) < THR_SIG:
                nois = np.mean(window)
            else:
                if len(nois_buf[:i]) > 0:
                    nois = np.mean(nois_buf[:i])

        thres_buf[i] = threshold
        nois_buf[i] = nois

        if h > 1:
            THR_SIG = nois + 0.50 * abs(threshold - nois)
        THR_buf[i] = THR_SIG

    if gr:
        fig, axs = plt.subplots(2, 1, sharex=True)
        axs[0].plot(test, label="Raw Signal")
        axs[0].plot(alarm * np.max(test), 'r', label="Detected Activity")
        axs[0].plot(THR_buf, '--g', label="Adaptive Threshold")
        axs[0].legend(loc="upper right")
        axs[0].set_title("Raw Signal and Detected Onsets of Activity")
        axs[0].grid(True)

        axs[1].plot(env, label="Smoothed Envelope")
        axs[1].plot(THR_buf, '--g', label="Adaptive Threshold")
        axs[1].plot(thres_buf, '--r', label="Activity Level")
        axs[1].plot(nois_buf, '--k', label="Noise Level")
        axs[1].legend(loc="upper right")
        axs[1].set_title("Smoothed Envelope (Hilbert Transform)")
        axs[1].grid(True)

        plt.tight_layout()
        plt.show()

    return alarm, env

def find_pulse_trains(x, fs=40):
    THD = 3.5 * fs
    walkflag = False
    w = []
    n = 0

    if len(x) > 2:
        for i in range(len(x) - 1):
            if x[i + 1] - x[i] < THD:
                if not walkflag:
                    walk = {'start': x[i], 'steps': 1}
                    walkflag = True
                    n += 1
                else:
                    walk['steps'] += 1
                    THD = 1.5 * fs + (x[i] - walk['start']) / walk['steps']
            else:
                if walkflag:
                    walk['end'] = x[i - 1]
                    w.append(walk)
                    walkflag = False
                    THD = 3.5 * fs

        if walkflag:
            if x[-1] - x[-2] < THD:
                walk['end'] = x[-1]
                walk['steps'] += 1
            else:
                walk['end'] = x[-2]
            w.append(walk)

    return w

def convert_w_to_set(w):
    s = np.zeros((len(w), 2), dtype=int)
    s[:, 0] = [entry['start'] for entry in w]
    s[:, 1] = [entry['end'] for entry in w]
    return s

def intersect(a, b):
    c = []
    ia, ib = 0, 0
    state = 3
    na, nb = a.shape[0], b.shape[0]

    while ia < na and ib < nb:
        if state == 1:
            if a[ia, 1] < b[ib, 0]:
                ia += 1
                state = 3
            elif a[ia, 1] < b[ib, 1]:
                c.append([b[ib, 0], a[ia, 1]])
                ia += 1
                state = 2
            else:
                c.append(list(b[ib]))
                ib += 1
        elif state == 2:
            if b[ib, 1] < a[ia, 0]:
                ib += 1
                state = 3
            elif b[ib, 1] < a[ia, 1]:
                c.append([a[ia, 0], b[ib, 1]])
                ib += 1
                state = 1
            else:
                c.append(list(a[ia]))
                ia += 1
        elif state == 3:
            if a[ia, 0] < b[ib, 0]:
                state = 1
            else:
                state = 2
    return np.array(c, dtype=int)

def pack_results(periods, peaks):
    w = []
    midswing = []

    for i in range(len(periods)):
        start = periods[i, 0]
        end = periods[i, 1]
        steps = [p for p in peaks if start <= p <= end]
        walk = {
            'start': start,
            'end': end,
            'steps': len(steps),
            'MidSwing': steps
        }

        if len(steps) > 2:
            step_time = np.mean(np.diff(steps))
            walk['start'] = int(np.floor(walk['start'] - 1.5 * step_time / 2))
            walk['end'] = int(np.floor(walk['end'] + 1.5 * step_time / 2))

        w.append(walk)
        midswing.extend(steps)

    # Merge overlapping periods
    i = 0
    while i < len(w) - 1:
        if w[i]['end'] >= w[i + 1]['start']:
            w[i]['end'] = w[i + 1]['end']
            w[i]['steps'] += w[i + 1]['steps']
            w[i]['MidSwing'].extend(w[i + 1]['MidSwing'])
            del w[i + 1]
        else:
            i += 1

    midswing = sorted(midswing)
    return w, midswing

def remove_drift_40hz(x):
    return signal.filtfilt([1, -1], [1, -0.9748], x)

def find_min_max(s, thr=None):
    d = np.diff(s)
    f = np.where(d[1:] * d[:-1] <= 0)[0] + 1
    mi = f[d[f] >= 0]
    ma = f[d[f] < 0]
    if thr is not None:
        ma = ma[s[ma] > thr]
        mi = mi[s[mi] < -thr]
    return mi, ma

def gsd_low_back_acc(imu_acc, fs, plot_results=False, time_vector = None):
    acc = imu_acc
    algorithm_target_fs = 40
    accN = np.linalg.norm(acc, axis=1)

    # resample accN from fs to 40 Hz
    accN40 = resamp_interp(accN, fs, algorithm_target_fs)

    accN_filt1 = signal.savgol_filter(accN40, 21, 7)
    accN_filt2 = signal.filtfilt([1, -1], [1, -0.9748], accN_filt1)
    accN_filt3 = pywt.cwt(accN_filt2, 10, 'gaus2', sampling_period=1/40)[0][0]
    accN_filt4 = signal.savgol_filter(accN_filt3, 11, 5)
    accN_filt5 = pywt.cwt(accN_filt4, 10, 'gaus2', sampling_period=1/40)[0][0]

    # Smoothing stages
    accN_filt6 = signal.convolve(accN_filt5, signal.windows.gaussian(10, std=2), mode='same') / 10
    accN_filt7 = signal.convolve(accN_filt6, signal.windows.gaussian(10, std=2), mode='same') / 10
    accN_filt8 = signal.convolve(accN_filt7, signal.windows.gaussian(15, std=2), mode='same') / 15
    accN_filt9 = signal.convolve(accN_filt8, signal.windows.gaussian(10, std=2), mode='same') / 10

    sig_det_actv = accN_filt9

    alarm, _ = hilbert_envelop(sig_det_actv, smooth_window=20, threshold_style=1, duration=algorithm_target_fs, gr=0)
    walkLowBack = []
    if np.any(alarm):
        idx = groupfind(alarm > 0)
        for j in range(idx.shape[0]):
            if idx[j, 1] - idx[j, 0] <= 3 * algorithm_target_fs:
                alarm[idx[j, 0]:idx[j, 1]] = 0
            else:
                walkLowBack.extend(sig_det_actv[idx[j, 0]:idx[j, 1]])
        walkLowBack = np.array(walkLowBack)
        pksp, _ = signal.find_peaks(walkLowBack)
        pksn, _ = signal.find_peaks(-walkLowBack)
        pks = np.concatenate((walkLowBack[pksp], -walkLowBack[pksn]))
        th = np.percentile(pks[pks > 0], 5)
        f = sig_det_actv
    else:
        th = 0.15
        f = accN_filt4

    min_peaks, max_peaks = find_min_max(f, th)
    
    t1 = find_pulse_trains(max_peaks)
    t1 = [t for t in t1 if t['steps'] >= 4]
    t2 = find_pulse_trains(min_peaks)
    t2 = [t for t in t2 if t['steps'] >= 4]
    t_final = intersect(convert_w_to_set(t1), convert_w_to_set(t2))

    if t_final.size == 0:
        w = []
        midswing = []
    else:
        w, midswing = pack_results(t_final, max_peaks)
        if w:
            w[0]['start'] = max(0, w[0]['start'])
            w[-1]['end'] = min(len(sig_det_actv) - 1, w[-1]['end'])

    w_new = [walk for walk in w if walk['steps'] >= 5]

    walk_label = np.zeros(len(sig_det_actv), dtype=int)
    for walk in w_new:
        walk_label[walk['start']:walk['end']] = 1

    ind_no_wk = groupfind(walk_label == 0)
    for j in range(ind_no_wk.shape[0]):
        if ind_no_wk[j, 1] - ind_no_wk[j, 0] <= 3 * algorithm_target_fs:
            walk_label[ind_no_wk[j, 0]:ind_no_wk[j, 1]] = 1
    
    # This section will process and return GSD_Output
    GSD_Output = []
    if np.any(walk_label == 1):
        ind_wk = groupfind(walk_label == 1)
        for j in range(ind_wk.shape[0]):
            GSD_Output.append({
                'Start': ind_wk[j, 0] / algorithm_target_fs,
                'End': ind_wk[j, 1] / algorithm_target_fs,
                'fs': fs
            })
    else:
        print("No gait sequence(s) detected")

    if plot_results:
        plt.plot(sig_det_actv)
        plt.plot(walk_label, 'r', linewidth=2)
        plt.legend(['filtered accNorm', 'Walking'])
        plt.xlabel('samples (100Hz)')
        plt.show()

    return GSD_Output