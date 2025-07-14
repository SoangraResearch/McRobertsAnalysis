import matplotlib.pyplot as plt
import scipy
import numpy as np 
import pywt
import pandas as pd

def gait_parameters(hs_selected_idx,to_selected_idx,df,i,walk_start,walk_end,cad,fs,fs_HS_TO):
    '''
        Inputs: 
        hs_selected_idx = array containg index positions of heal strike
        to_selected_idx = array containg index positions of toe off
        df = data frame in which gait parameters are to be added
        i = walking index
        walk_start = index position in 100hz signal where walking started
        walk_end = index position in 100hz signal where walking ended
        cad = array containing cadence calculted for each second
        fs = sampling rate of original signal
        fs_HS_TO = sampling rate used to calculate the heal strike and toe off
    '''
    
    #print(hs_selected_idx.size)
    #print(to_selected_idx.size)
    #separate foot 1 and foot 2 hs, TO
    foot1_hs = hs_selected_idx[::2]
    foot2_hs = hs_selected_idx[1::2]
    foot2_to = to_selected_idx[::2]
    foot1_to = to_selected_idx[1::2]
    #print("heal strike toe off length")
    #print(foot1_hs.size)
    #print(foot2_hs.size)
    #print(foot1_to.size)
    #print(foot2_to.size)

    if(to_selected_idx[0] < hs_selected_idx[0]): # checking if we have toe off detected before heal strike
        to_selected_idx_updated = to_selected_idx[1:] # removing the first toe off from our data
        #print("Updated to off length")
        #print(to_selected_idx_updated.size)
        foot2_to = to_selected_idx_updated[::2]
        foot1_to = to_selected_idx_updated[1::2]

    lists = [foot1_hs,foot2_hs,foot1_to,foot2_to]
    min_length = min(len(lst) for lst in lists)
    #print(min_length)
    foot1_hs = foot1_hs[:min_length]
    foot2_hs = foot2_hs[:min_length]
    foot1_to = foot1_to[:min_length]
    foot2_to = foot2_to[:min_length]
    lists = np.array([foot1_hs,foot2_hs,foot1_to,foot2_to])

    sizes = [lst.size for lst in lists]
    #print("size of updated hs to ",sizes)

    # foot1 gait cycle parameters
    gait_cycle_time_foot1 = np.diff(foot1_hs)
    dst1_foot1 = foot2_to[:-1] - foot1_hs[:-1] #double support time before foot2 toe off
    dst1_foot2 = foot1_to[:-1] - foot2_hs[:-1] #double support time before foot1 toe off
    sst1_foot1 = foot2_hs[:-1] - foot2_to[:-1] #single support time on foot1
    sst1_foot2 = foot1_hs[1:] - foot1_to[:-1]#single support time on foot2
    stance_time1_foot1 = foot1_to[:-1] - foot1_hs[:-1] #stance time on foot1
    stance_time1_foot2 = foot1_hs[1:] - foot2_hs[:-1]
    swing_time1_foot1 = sst1_foot2 #swing time of foot1
    swing_time1_foot2 = sst1_foot1 #swing time of foot2
        
    # foot2 gait cycle parameters
    gait_cycle_time_foot2 = np.diff(foot2_hs)
    dst2_foot2 = foot1_to[:-1] - foot2_hs[:-1] #double support time before foot1 toe off
    dst2_foot1 = foot2_to[1:] - foot1_hs[1:] #double support time before foot2 toe off
    sst2_foot2 = foot1_hs[1:] - foot1_to[:-1] #single support time on foot2
    sst2_foot1 = foot2_hs[1:] - foot2_to[1:]#single support time on foot1
    stance_time2_foot2 = foot1_hs[1:] - foot2_hs[:-1] #stance time on foot1
    stance_time2_foot1 = foot1_to[1:] - foot1_hs[1:]
    swing_time2_foot1 = sst2_foot2 #swing time of foot1
    swing_time2_foot2 = sst2_foot1 #swing time of foot2
    
    lists = [foot1_hs,foot2_hs,foot1_to,foot2_to,gait_cycle_time_foot1,gait_cycle_time_foot2,dst1_foot1,dst1_foot2,dst2_foot1,dst2_foot2,
            sst1_foot1,sst1_foot2,sst2_foot1,sst2_foot2,stance_time1_foot1,stance_time1_foot2,stance_time2_foot1,stance_time2_foot2,
            swing_time1_foot1,swing_time1_foot2,swing_time2_foot1,swing_time2_foot2]

    names= ['foot1_hs','foot2_hs','foot1_to','foot2_to','gait_cycle_time_foot1','gait_cycle_time_foot2','dst1_foot1','dst1_foot2','dst2_foot1','dst2_foot2',
            'sst1_foot1','sst1_foot2','sst2_foot1','sst2_foot2','stance_time1_foot1','stance_time1_foot2','stance_time2_foot1','stance_time2_foot2',
            'swing_time1_foot1','swing_time1_foot2','swing_time2_foot1','swing_time2_foot2']
    
    # Find the maximum length of the arrays
    max_len = max(len(arr) for arr in lists)
    #print("max_length is ",max_len)

    padded_lists = []
    # Pad each array with NaN values to make them the same length
    for lst in lists:
        lst_nan = np.pad(lst, (0, max_len - len(lst)), mode='constant', constant_values=np.nan)
        padded_lists.append(lst_nan)
    padded_lists = np.array(padded_lists)
    lists = padded_lists

    walking_index = np.full(max_len, np.nan, dtype=float)
    walking_index[0] = i+1
    #print("walking index ",walking_index.shape)

    # finding number steps for the current walking period
    steps = np.full(max_len, np.nan, dtype=float) # creted the array

    # altering the walking indices to match with the cad array
    walk_start = walk_start//fs_HS_TO
    walk_end = walk_end//fs_HS_TO
    steps[0] = sum(cad[walk_start:walk_end+1])

    time = np.full(max_len,np.nan, dtype=float)
    time[0] = walk_end - walk_start - 1

    start_index= np.full(max_len, np.nan, dtype=float)
    end_index = np.full(max_len, np.nan, dtype=float)
    # for the original signal
    start_index[0] = (walk_start)*fs 
    end_index[0] = (walk_end+1)*fs -1

    

    #print("End index",end_index.size)
    


    new_row = pd.DataFrame({'walking_index':walking_index,'steps':steps,'time':time, 'start_index' : start_index, 'end_index' : end_index, 'foot1_hs' : lists[0],'foot2_hs':lists[1],'foot1_to':lists[2],'foot2_to':lists[3],'gait_cycle_time_foot1':lists[4],'gait_cycle_time_foot2' :lists[5],'dst1_foot1':lists[6],'dst1_foot2':lists[7],'dst2_foot1':lists[8],'dst2_foot2':lists[9],
            'sst1_foot1':lists[10],'sst1_foot2':lists[11],'sst2_foot1':lists[12],'sst2_foot2':lists[13],'stance_time1_foot1':lists[14],'stance_time1_foot2':lists[15],'stance_time2_foot1':lists[16],'stance_time2_foot2':lists[17],
            'swing_time1_foot1':lists[18],'swing_time1_foot2':lists[19],'swing_time2_foot1':lists[20],'swing_time2_foot2':lists[21]})
    df = pd.concat([df, new_row], ignore_index=True)

    return df
    

def get_scales(wavelet, max_freq, fs):
    fc = pywt.central_frequency(wavelet)
    fa = max_freq
    sampling_period = 1/fs
    scales = fc/(fa*sampling_period)
    return scales

def get_wavelet(wavelet_name):
    discrete_wavelets = ['db2']
    continuous_wavelets = ['gaus1', 'gaus2']
    if wavelet_name in discrete_wavelets:
        wavelet = pywt.Wavelet(wavelet_name)
    elif wavelet_name in continuous_wavelets:
        wavelet = pywt.ContinuousWavelet(wavelet_name)
    else:
        print("ERROR: wavelet type %s not a valid type for this method" % wavelet_name)
        raise ValueError
    return wavelet

def get_hs_to_wavelet(acc_ap, fs, turning, plot_figure, save_fig_name, wavelet_type_straight="gaus1", wavelet_type_turning="gaus1"):

    if (turning):
        print('This is a turning dataset, will use %s' % wavelet_type_turning)
    else:
        print('This is a straight walking dataset, will %s' % wavelet_type_straight)

    # Preprocess acceleration data (see paragraph "Extraction of HS and TO from
    # IMU" lines 1-4 in Pham et al., 2017)
    acc_detrend = scipy.signal.detrend(acc_ap)
    fn = fs/2
    b, a = scipy.signal.butter(2, 10/fn, 'low')
    acc_ap_pp = scipy.signal.filtfilt(b, a, acc_detrend, axis=0)

    # Integrate detrended and filtered acceleration data (see paragraph
    # "Extraction of HS and TO from IMU" lines 4-7 in Pham et al., 2017)
    signal_len = acc_ap_pp.shape[0]
    time_vector = np.arange(0, signal_len) / fs
    acc_int = scipy.integrate.cumulative_trapezoid(acc_ap_pp, x=time_vector, axis=0, initial=0)

    # Find the dominant frequency of the acceleration (see paragraph
    # "Extraction of HS and TO from IMU" lines 8-15 in Pham et al., 2017)
    half_idx = int(signal_len/2)
    f_x = scipy.fft.fft(acc_ap_pp) / signal_len
    freqs = np.fft.fftfreq(signal_len, d=1/fs)
    freqs_halfside = freqs[0:half_idx]
    power = 10*np.log10(np.abs(f_x[0:half_idx]))
    max_power = power.max()
    max_idx = power.argmax()
    max_freq = freqs_halfside[max_idx]
    print("Dominant frequency: %f, with power: %f" % (max_freq, max_power))

    # Select wavelet for smoothing (see paragraph "Extraction of HS and TO from IMU" lines 4-7 in Pham et al., 2017)
    wavelet_dcwt1 = pywt.ContinuousWavelet('gaus1')
    scales = get_scales(wavelet_dcwt1, max_freq, fs)

    # Differentiate integrated signal to smooth acceleration signal
    acc_wave, _ = pywt.cwt(acc_int, scales, wavelet_dcwt1)
    acc_wave = -acc_wave[0,:] # Invert to match original signal, see Pham and McCamley
    acc_wave = np.real(acc_wave)

    # Find heel strike events (see Fig. 2 in Pham et al., 2017)
    # Here, we want to find local minima. Apply findpeaks to negative signal.
    acc_wave_detrended = scipy.signal.detrend(acc_wave)
    hs_idx, _ = scipy.signal.find_peaks(-acc_wave_detrended)

    # Find toe off events (see paragraph "Adaptation of the cwt to the Steps
    # in the Home-Like Assessment" in Pham et al., 2017).
    # Paper recommends db2 for straight walking and gaus2 for turning, 
    # although here gaus1 was found to work best.
    if (turning):
        wavelet_dcwt2 = get_wavelet(wavelet_type_turning)
    else:
        wavelet_dcwt2 = get_wavelet(wavelet_type_straight)
    scales = get_scales(wavelet_dcwt2, max_freq, fs)
    acc_wave_2, _ = pywt.cwt(acc_wave, scales, wavelet_dcwt2)
    acc_wave_2 = -acc_wave_2[0,:]
    acc_wave_2 = np.real(acc_wave_2)

    # Find maxima of differentiated signal to get TO
    to_idx, _ = scipy.signal.find_peaks(acc_wave_2)
    
    # Peak selection by magnitude. From paper:
    # "HS/TO was as follows: magnitude >40% of the mean of all peaks detected by
    # the findpeaks function."
    # The limit has here been modified to 0.2 for HS which was found to work better.
    pks_hs = acc_wave[hs_idx]
    pks_to = acc_wave_2[to_idx]
    hs_mean = np.mean(pks_hs)
    to_mean = np.mean(pks_to)
    hs_selected_idx = hs_idx[np.where(pks_hs < hs_mean*0.2)]
    to_selected_idx = to_idx[np.where(pks_to > to_mean*0.4)]

    # Some validation.
    # HS has to be followed by TO. otherwise mark as invalid.
    invalid_hs_idx = []
    for i in range(0, len(hs_selected_idx)-1):
        hs = hs_selected_idx[i]
        next_hs = hs_selected_idx[i+1]
        next_to = to_selected_idx[to_selected_idx > hs]
        if len(next_to) < 1:
            # No found TO. Mark HS as invalid.
            invalid_hs_idx = np.append(invalid_hs_idx, hs)
        else:
            # Found next TO. Make sure it's in the right order compared to upcoming HS.
            next_to = next_to[0]
            if next_hs < next_to:
                invalid_hs_idx = np.append(invalid_hs_idx, hs)
        
    # If the very last HS is not followed by TO, mark as invalid.
    if hs_selected_idx[-1] > to_selected_idx[-1]:
        invalid_hs_idx = np.append(invalid_hs_idx, hs_selected_idx[-1])

    # Convert to int array
    invalid_hs_idx = np.array(invalid_hs_idx)
    invalid_hs_idx = invalid_hs_idx.astype(int)

    # Get the corresponding times
    hs_times = time_vector[hs_selected_idx]
    to_times = time_vector[to_selected_idx]
    invalid_hs_times = time_vector[invalid_hs_idx]

    if plot_figure:
        print("Plotting")
        plt.figure(0)
        figure = plt.gcf() # get current figure
        plt.rcParams["figure.figsize"] = (16,8)
        plt.rcParams.update({'font.size': 20})
        plt.plot(time_vector, acc_ap_pp, 'b--', label='acc_ap')
        plt.plot(time_vector, acc_wave_detrended, color="grey", linestyle="dotted", label='dcwt1')
        plt.plot(time_vector, acc_wave_2, 'k', label='dcwt2')
        plt.plot(hs_times, acc_wave_detrended[hs_selected_idx], linestyle='None', color='red', label='HS', marker="*",  markersize=10)
        plt.plot(to_times, acc_wave_2[to_selected_idx], linestyle='None', color='lime', label='TO', marker="*",  markersize=10)
        plt.plot(invalid_hs_times, acc_wave_detrended[invalid_hs_idx], linestyle='None', color='orange', label='HS invalid', marker="*",  markersize=10)
        plt.title(save_fig_name)
        plt.xlabel('Time [s]')
        plt.legend(loc="upper right")
        
        if save_fig_name is not None:
            plt.savefig(save_fig_name, dpi = 100)
            plt.close()
        else:
            plt.show()

    return hs_selected_idx, to_selected_idx, invalid_hs_idx


