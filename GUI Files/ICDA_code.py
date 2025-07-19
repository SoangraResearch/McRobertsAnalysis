from scipy.signal import filtfilt
from scipy.interpolate import interp1d
from scipy.signal import convolve
from scipy.io import loadmat
from GSDB_code import resamp_interp
import pywt
import numpy as np

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

    Num = loadmat("C:/Users/ahala/OneDrive/Desktop/SoangraResearch/McRobertsAnalysis/Mobilise-D-TVS-Recommended-Algorithms-master/ICDA/Library/FIR-2-3Hz-40.mat")['Num'].flatten()

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


def step_detection(imu_acc, GS, fs, plot_results=False):
    acc_v = imu_acc[:, 0]  # vertical acceleration

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
        return []

    if plot_results:
        Num = loadmat("C:/Users/ahala/OneDrive/Desktop/SoangraResearch/McRobertsAnalysis/Mobilise-D-TVS-Recommended-Algorithms-master/ICDA/Library/FIR-2-3Hz-40.mat")['Num'].flatten()  

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