import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import resample
import numpy as np
import matplotlib.pyplot as plt

def get_fields(data, curr_structure='data', rfields=None):
    if rfields is None:
        rfields = []

    current = eval(curr_structure)

    for key in current:
        value = current[key]
        new_path = f"{curr_structure}.{key}"
        if isinstance(value, dict):
            rfields = get_fields(data, new_path, rfields)
        else:
            rfields.append(new_path)
    return rfields

def gsd_iluz(imu, time_vector=None, plot_results=False, force_walking = False):
    algorithm_target_fs = 100
    algorithm_output_fs = 100

    WinS = algorithm_target_fs * 3  # window size
    OL = WinS // 2                  # overlap
    activity_thresh = 0.01

    try:
        imu_preprocessed = preprocessing_standardized(imu, algorithm_target_fs)

        gait_sequences_bool, v_acc = WBDet_Sine(
            imu_preprocessed,
            algorithm_target_fs,
            WinS,
            OL,
            activity_thresh,
            plot_results,
            force_walking = force_walking
        )

        if force_walking:
            gait_sequences_bool = np.ones(len(gait_sequences_bool), dtype=int)

        GSD = save_gsd_result(gait_sequences_bool, algorithm_output_fs, time_vector)
    except Exception as e:
        print(f"Warning: GSD algorithm failed: {e}")
        GSD = []

    return GSD, gait_sequences_bool, v_acc

def preprocessing_standardized(IMU, algorithm_target_fs):
    acc = IMU['LowerBack']['Acc']
    gyr = IMU['LowerBack']['Gyr']
    fs_acc = IMU['LowerBack']['Fs']['Acc']

    if algorithm_target_fs != fs_acc:
        acc_resampled = resample(acc, int(len(acc) * algorithm_target_fs / fs_acc))
        gyr_resampled = resample(gyr, int(len(gyr) * algorithm_target_fs / fs_acc))
        imu_preprocessed = np.hstack([acc_resampled, gyr_resampled])
    else:
        imu_preprocessed = np.hstack([acc, gyr])

    return imu_preprocessed

def save_gsd_result(walking_bool_vector, algorithm_output_fs, time_vector=None):
    if np.all(walking_bool_vector == 0):
        return [{
            'Start': float('nan'),
            'End': float('nan'),
            'GSD_fs': algorithm_output_fs
        }]

    walking_bool_vector = walking_bool_vector.flatten()
    edges = np.diff(walking_bool_vector.astype(int))
    starts = list(np.where(edges == 1)[0] + 1)
    ends = list(np.where(edges == -1)[0] + 1)

    if walking_bool_vector[0] == 1:
        starts.insert(0, 0)
    if walking_bool_vector[-1] == 1:
        ends.append(len(walking_bool_vector))

    gait_sequences = []
    for s, e in zip(starts, ends):
        gait_sequences.append({
            'Start': s / algorithm_output_fs,
            'End': e / algorithm_output_fs,
            'GSD_fs': algorithm_output_fs
        })

    return gait_sequences

def find_peaks(vec, th, do_plot=0):
    vec = np.asarray(vec)
    vec_s = vec - np.mean(vec)  # normalize
    A = np.append(0, vec_s) * np.append(vec_s, 0)
    Z = np.where(A < 0)[0]

    if len(Z) == 0:
        return []

    min_dist = np.where(np.diff(np.append(0, Z)) > th)[0]
    bumps = Z[min_dist]
    Bp = bumps[::2]

    if len(Bp) < 2:
        return []

    diff_bp = np.diff(np.append(0, Bp))
    try:
        mean_diff = np.mean(diff_bp[1:-1])
        miss_p = np.where(diff_bp[1:-1] > 1.2 * mean_diff)[0] + 1
    except:
        miss_p = []

    if len(miss_p) != 0:
        Bn = np.sort(np.append(Bp, Bp[miss_p - 1] + ((Bp[miss_p] - Bp[miss_p - 1]) // 2)))
    else:
        Bn = Bp

    L_Bp = len(Bn)

    if L_Bp == 0:
        return []

    if len(vec_s) > Bn[-1] + 2:
        Bn = np.append(Bn, len(vec_s))
    else:
        L_Bp -= 1

    P_L = []
    for z in range(L_Bp):
        segment = vec_s[Bn[z] + 1 : Bn[z + 1] - 1]
        if len(segment) == 0:
            continue
        peak_idx = np.argmax(segment)
        P_L.append(Bn[z] + 1 + peak_idx)

    if do_plot:
        plt.figure()
        plt.plot(vec_s, label='Signal')
        plt.stem(P_L, vec_s[P_L], linefmt='r-', markerfmt='ro', label='Peaks')
        plt.stem(Bn, vec_s[Bn], linefmt='g-', markerfmt='go', label='Zero-crossings')
        plt.legend()
        plt.show()

    return P_L

# WBDet_Sine.m file

from scipy.signal import firwin, lfilter
from scipy.signal import convolve as conv
from numpy.lib.stride_tricks import sliding_window_view

def WBDet_Sine(imu, sample_rate, win_size, overlap, activity_thresh, plot_results=False, force_walking = False):
    acc = imu[:, :3]
    v_acc = acc[:, 0]
    ap_acc = acc[:, 2]

    # Bandpass filter: 0.5–3 Hz
    b = firwin(201, [0.5, 3], pass_zero=False, fs=sample_rate)
    v_filt = lfilter(b, 1.0, v_acc)
    ap_filt = lfilter(b, 1.0, ap_acc)

    # Skip the first second of data
    v_filt = v_filt[int(sample_rate):]
    ap_filt = ap_filt[int(sample_rate):]

    # Convolve with sine template
    template = np.sin(2 * np.pi * np.linspace(0, 0.5, int(sample_rate / 2)))
    v_conv = conv(v_acc - 1, template, mode='full')[len(template):]
    ap_conv = conv(ap_acc, template, mode='full')[len(template):]

    if force_walking:
        gait_bool = np.ones(len(v_acc), dtype=int)
    else:
        # Buffer and activity thresholding
        v_buf = sliding_window_view(v_conv, window_shape=win_size)[::(win_size - overlap)]
        stds = np.std(v_buf, axis=1)
        active_windows = np.where(stds > activity_thresh)[0]

        gait_bool = np.zeros(len(v_acc), dtype=int)
        for win_idx in active_windows:
            start = win_idx * (win_size - overlap)
            end = start + win_size
            if end > len(gait_bool):
                continue
            gait_bool[start:end] = 1  # Placeholder logic

    if plot_results:
        import matplotlib.pyplot as plt
        plt.plot(v_acc, label='Vertical Acc')
        plt.plot(gait_bool * np.max(v_acc), label='Detected Gait')
        plt.legend()
        plt.show()

    return gait_bool, v_acc

# driver.m file
import os
import json
from scipy.io import loadmat, savemat

def driver(indir, outdir):
    try:
        # Load the .mat file
        mat_data = loadmat(os.path.join(indir, 'data.mat'), struct_as_record=False, squeeze_me=True)
        data = mat_data['data']

        # Get all field paths ending in 'LowerBack.Acc'
        all_fields = get_fields(data, 'data', [])
        acc_fields = [f for f in all_fields if 'LowerBack.Acc' in f and 'SU_INDIP' not in f]

        GSD_Output = {}
        for path in acc_fields:
            field_parts = path.split('.')[1:-2]  # remove 'data.' prefix and '.Acc'
            imu_struct = data
            for part in field_parts:
                imu_struct = getattr(imu_struct, part) if hasattr(imu_struct, part) else imu_struct[part]

            gsd_result = GSD_Iluz(imu_struct)  # your gait detection logic here
            gsd_path = field_parts + ['GSD']

            d = GSD_Output
            for key in gsd_path[:-1]:
                d = d.setdefault(key, {})
            d[gsd_path[-1]] = gsd_result

        # Save JSON
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, 'GSDA_Output.json'), 'w') as f:
            json.dump({'GSDA_Output': GSD_Output}, f, indent=2)

        # Save MAT
        savemat(os.path.join(outdir, 'GSDA_Output.mat'), {'GSD_Output': GSD_Output})

        return 'ok'

    except Exception as e:
        print(f"Error during processing: {e}")
        return 'error'
