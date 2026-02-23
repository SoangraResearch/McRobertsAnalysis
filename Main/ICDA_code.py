from scipy.signal import filtfilt
from scipy.interpolate import interp1d
from scipy.signal import convolve
from scipy.io import loadmat
from GSDB_code import resamp_interp
import pywt
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path

#automatically finds file paths
def find_mcroberts_root():
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "McRobertsAnalysis"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not find 'McRobertsAnalysis' folder in any parent directory.")

MCROBERTS_ROOT = find_mcroberts_root()
FIR_FILTER_PATH = MCROBERTS_ROOT / "Mobilise-D-TVS-Recommended-Algorithms-master" / "ICDA" / "Library" / "FIR-2-3Hz-40.mat"

def remove_drift_40hz(x):
    return filtfilt([1, -1], [1, -0.9748], x)

def max_peaks_between_zc(signal):
    """ Emulates MaxPeaksBetweenZC by detecting peaks between zero crossings. """
    zero_crossings = np.where(np.diff(np.signbit(signal)))[0]
    peaks = []
    peak_indices = []
    
    for i in range(len(zero_crossings) - 1):
        seg = signal[zero_crossings[i]:zero_crossings[i+1]]
        if len(seg) == 0:
            continue
        local_peak_idx = np.argmax(np.abs(seg))
        true_idx = zero_crossings[i] + local_peak_idx
        peaks.append(signal[true_idx])
        peak_indices.append(true_idx)
    
    return np.array(peaks), np.array(peak_indices)

def sd_algo_amc(accV, fs):
    algorithm_target_fs = 40

    # resample using same method from earlier translation
    accV40 = resamp_interp(accV, fs, algorithm_target_fs)

    Num = loadmat(str(FIR_FILTER_PATH))['Num'].flatten()

    len_padd = 10000 * len(Num)
    accV40_zp = np.pad(accV40, pad_width=len_padd, mode='wrap')
    accV40_lpf = filtfilt(Num, [1], remove_drift_40hz(accV40_zp))
    accV40_lpf_rmzp = accV40_lpf[len_padd:-len_padd]

    accVLPInt = np.cumsum(accV40_lpf_rmzp) / algorithm_target_fs
    accVLPIntCwt, _ = pywt.cwt(accVLPInt, 9, 'gaus2', sampling_period=1 / algorithm_target_fs)
    accVLPIntCwt = accVLPIntCwt[0] - np.mean(accVLPIntCwt[0])

    pks1, ipks1 = max_peaks_between_zc(accVLPIntCwt)
    IC = ipks1[pks1 < 0] / algorithm_target_fs  # Initial Contacts

    accVLPIntCwt2, _ = pywt.cwt(accVLPIntCwt, 9, 'gaus2', sampling_period=1 / algorithm_target_fs)
    accVLPIntCwt2 = accVLPIntCwt2[0] - np.mean(accVLPIntCwt2[0])

    pks2, ipks2 = max_peaks_between_zc(accVLPIntCwt2)
    FC = ipks2[pks2 > 0] / algorithm_target_fs  # Final Contacts

    return IC, FC


def step_detection(imu_acc, GS, fs, plot_results=False, original_time_array=None):
    acc_v = imu_acc[:, 0]  # vertical acceleration

    #print(GS)

    print("is instance: " + (str)(isinstance(GS, list)))
    print("length of GS: " + (str)(len(GS)))
    print("Start in GS: " + (str)(('GaitSequence_Start' in GS[0])))
    print("End in GS: " + (str)(('GaitSequence_End' in GS[0])))

    if isinstance(GS, list) and len(GS) > 0 and 'Start' in GS[0] and 'End' in GS[0]:
        SD_Output = []

        for j in range(len(GS)):
            start = round(fs * GS[j]['Start'])
            stop = round(fs * GS[j]['End'])
            acc_v_gs = acc_v[start:stop]

            try:
                IC_rel, _ = sd_algo_amc(acc_v_gs, fs)  # assumes this function is defined
                IC = GS[j]['Start'] + IC_rel
                GS[j]['IC'] = IC.tolist()
            except Exception as e:
                print(f"Warning: Step detection failed for segment {j}: {e}")
                GS[j]['IC'] = []

        SD_Output = GS
    else:
        print("empty steps array")
        return []

    if plot_results:
        Num = loadmat(str(FIR_FILTER_PATH))['Num'].flatten()

        fs_algo = 40
        IC_all_sig = np.concatenate([np.array(g['IC']) for g in GS if 'IC' in g and len(g['IC']) > 0])
        ICs = np.round(IC_all_sig * fs).astype(int)

        acc_v_40 = resamp_interp(acc_v, fs, fs_algo)
        acc_v_lpf = filtfilt(Num, [1], remove_drift_40hz(acc_v_40))
        acc_v_lpf_int = np.cumsum(acc_v_lpf) / fs_algo
        acc_v_lpf_cwt, _ = pywt.cwt(acc_v_lpf_int, 9, 'gaus2', sampling_period=1 / fs_algo)
        acc_v_lpf_cwt = acc_v_lpf_cwt[0] - np.mean(acc_v_lpf_cwt[0])
        acc_v_processed = resamp_interp(acc_v_lpf_cwt, fs_algo, fs)

        plt.figure()
        plt.plot(np.arange(len(acc_v_processed)), acc_v_processed, 'b', label='accV (processed)')
        plt.plot(ICs, acc_v_processed[ICs], 'ro', label='Initial Contacts (IC)')
        plt.legend()
        plt.title("Step Detection")
        plt.xlabel("Samples")
        plt.show()

    return SD_Output

def seconds_to_datetime(seconds_offset, time_array, sampling_rate):
    if time_array is None or len(time_array) == 0:
        return "N/A (no time reference)"
            
    try:
        sample_index = int(seconds_offset * sampling_rate)
                
        if sample_index >= len(time_array):
            sample_index = len(time_array) - 1
        elif sample_index < 0:
            sample_index = 0
                
        dt = time_array[sample_index]
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        return f"Error converting time: {e}"

#TODO: get working for GSDA
def filter_and_print_long_segments(GS, min_duration=30, original_time_array=None, fs=100):
    print(f"\n--- Filtering segments longer than {min_duration} seconds ---")
    
    if not isinstance(GS, list) or len(GS) == 0:
        print("No segments to filter")
        return []
    
    long_segments = []
    
    for i, segment in enumerate(GS):
        if 'Start' in segment and 'End' in segment:
            duration = segment['End'] - segment['Start']
            
            start_dt = seconds_to_datetime(segment['Start'], original_time_array, fs)
            end_dt = seconds_to_datetime(segment['End'], original_time_array, fs)
            
            print(f"Segment {i}: Start={segment['Start']:.3f}s ({start_dt}), End={segment['End']:.3f}s ({end_dt}), Duration={duration:.3f}s")
            
            if duration > min_duration:
                long_segments.append(segment)
                print(f"  -> LONG SEGMENT: Duration {duration:.3f}s > {min_duration}s threshold")
        else:
            print(f"Segment {i}: Missing Start/End keys")
    
    print(f"\nTotal segments: {len(GS)}")
    print(f"Long segments (>{min_duration}s): {len(long_segments)}")
    
    if long_segments:
        print("\nLong segments details:")
        for i, segment in enumerate(long_segments):
            duration = segment['End'] - segment['Start']
            start_dt = seconds_to_datetime(segment['Start'], original_time_array, fs)
            end_dt = seconds_to_datetime(segment['End'], original_time_array, fs)
            print(f"  Long segment {i+1}: {duration:.3f}s")
            print(f"    Start: {segment['Start']:.3f}s ({start_dt})")
            print(f"    End: {segment['End']:.3f}s ({end_dt})")
    else:
        print(f"No segments longer than {min_duration} seconds found")
    
    return long_segments