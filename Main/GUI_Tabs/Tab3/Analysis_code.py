import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import resample
from Main.GUI_Tabs.Tab3.Analysis_Plots import linear_plot, nonlinear_plot
from Non_GUI.Analysis_Code.gait_functions.walking import find_walking
from Non_GUI.Analysis_Code.gait_functions.hs_to_detection import get_hs_to_wavelet # function to detect heal strike and toe off from the walking data
from Non_GUI.Analysis_Code.gait_functions.hs_to_detection import gait_parameters  # function to calculate gait parameters from heal strike and toe off

from Non_GUI.Analysis_Code.non_linear_functions.ami_stergio import AMI_Stergiou
from Non_GUI.Analysis_Code.non_linear_functions.fnn import FNN
from Non_GUI.Analysis_Code.non_linear_functions.ent_Ap import Ent_Ap
from Non_GUI.Analysis_Code.non_linear_functions.ent_symbolic import Ent_Symbolic
from Non_GUI.Analysis_Code.non_linear_functions.entMSPlus import Ent_MS_Plus
from Non_GUI.Analysis_Code.non_linear_functions.entPermu import Ent_Permu
from Non_GUI.Analysis_Code.non_linear_functions.lye_R import LyE_R
from Non_GUI.Analysis_Code.non_linear_functions.lye_W import LyE_W
from Non_GUI.Analysis_Code.non_linear_functions.rqa import RQA
from Non_GUI.Analysis_Code.non_linear_functions.ent_Samp import Ent_Samp

def linear_analysis(filename, plot_frame, assume_walking=False):
    fs = 100

    accleration = pd.read_csv(filename)
    print("file " + filename)

    accleration['TgF'] = np.sqrt(accleration['Ax']**2+accleration['Ay']**2+accleration['Az']**2)
    R_acc = accleration['TgF'] - 1 #resultant acceleration adjusted with gravity

    vm = np.array(R_acc) #converting to numpy array

    print("Numpy array size: ")
    print(np.size(vm))

    ## Parameters for find_walking and get_hs_to_wavelet function
    fs_walking = 10 # sampling rate required by find_walking function
    num_samples = int(np.size(vm)*fs_walking/fs)
    vm_resample = resample(vm, num_samples)

    print("num_samples:" )
    print(num_samples)

    # For the function to work properly it needs the number of samples to be a multiple of frequency(10hz)
    # the function arranges the signal into matrix with each column containing 10 samples ie data for 1 second
    num_elements_to_use = (vm_resample.size // fs_walking) * fs_walking

    print("num_elements to use: ")
    print(num_elements_to_use)

    vm_bout = vm_resample[:num_elements_to_use]

    print("vm_bout: ")
    print(vm_bout)

    print("RMS of vm_bout:", np.sqrt(np.mean(vm_bout**2)))

    # parameters for find walking function
    min_amp = 0.3 # amplitude threshold (in g ) 
    T = 3 # minimum walking duration (in seconds)
    delta = 20 #maximum difference between consecutive peaks (in multiplication of 0.05Hz)
    alpha = 1.6 #maximum ratio between dominant peak below and within step frequency range
    beta = 2.5 # maximum ratio between dominant peak above and within step frequency range
    step_freq = (1.4,2.3) #step frequency range (in Hz or steps per second)

    # heal strike toe off detection
    fs_HS_TO = 100 #sampling frequency needed by the function
    turning = 0

    if assume_walking:
        print("assuming walking")
        walking = np.array([[0, len(vm) * fs_HS_TO // fs]])
        cad = np.array([])
    else:
        cad = find_walking(vm_bout, 10, min_amp, step_freq, alpha, beta, T, delta)
        walking = _walking_period_detection(cad, fs_HS_TO)
        print("cadence: ")
        print(cad)
        print(f"Walking periods found: {len(walking) if len(walking.shape) > 0 else 0}")

    if len(walking) == 0:
        print("No walking periods found. Returning empty results.")
        empty_df = pd.DataFrame(columns=['walking_index','steps','time', 'start_index', 'end_index', 
                                 'foot1_hs','foot2_hs','foot1_to','foot2_to',
                                 'gait_cycle_time_foot1','gait_cycle_time_foot2',
                                 'dst1_foot1','dst1_foot2','dst2_foot1','dst2_foot2',
                                 'sst1_foot1','sst1_foot2','sst2_foot1','sst2_foot2',
                                 'stance_time1_foot1','stance_time1_foot2','stance_time2_foot1','stance_time2_foot2',
                                 'swing_time1_foot1','swing_time1_foot2','swing_time2_foot1','swing_time2_foot2'])
        return empty_df, []

    # Display the results
    print("Linear Analysis: ")
    print("walking: ")
    print(walking)

    az = accleration['Az']

    num_samples = int(len(az) * fs_HS_TO / fs)  # Calculate the number of samples in the resampled signal

    resampled_az = resample(az, num_samples)

    #Create a dataframe which will contain the walking period index and gait parameters(in seconds)

    df = pd.DataFrame(columns=['walking_index','steps','time', 'start_index', 'end_index', 'foot1_hs','foot2_hs','foot1_to','foot2_to','gait_cycle_time_foot1','gait_cycle_time_foot2','dst1_foot1','dst1_foot2','dst2_foot1','dst2_foot2',
         'sst1_foot1','sst1_foot2','sst2_foot1','sst2_foot2','stance_time1_foot1','stance_time1_foot2','stance_time2_foot1','stance_time2_foot2',
         'swing_time1_foot1','swing_time1_foot2','swing_time2_foot1','swing_time2_foot2'])
    
    print("len of walking: ", len(walking))

    plots = []

    for i in range(len(walking)):
        walk_start = walking[i,0]
        walk_end= walking[i,1]
        walk = resampled_az[walk_start:walk_end]

        # Get heal strike and toe off
        hs_selected_idx, to_selected_idx, invalid_hs_idx, time_vector, acc_ap_pp, acc_wave_detrended, acc_wave_2, hs_times, to_times, invalid_hs_times = get_hs_to_wavelet(walk, fs_HS_TO, turning, 0, "No plot name", wavelet_type_straight="gaus1", wavelet_type_turning="gaus1")
        # converted to float and dividing by 100 to get results in units of second
        hs_selected_idx_new = (hs_selected_idx.astype(float))/100
        to_selected_idx_new = (to_selected_idx.astype(float))/100

        # get gait parameters
        print("getting gait parameters")
        print("hs_selected_idx_new")
        print(hs_selected_idx_new)
        print("to_selected_idx_new")
        print(to_selected_idx_new)

        if len(hs_selected_idx_new) < 2 or len(to_selected_idx_new) < 1:
            print(f"Warning: Walking bout {i} has insufficient HS ({len(hs_selected_idx_new)}) or TO ({len(to_selected_idx_new)}) detections. Skipping.")
            fig = linear_plot(time_vector, acc_ap_pp, acc_wave_detrended, acc_wave_2, hs_times, hs_selected_idx, to_times, to_selected_idx, invalid_hs_idx, invalid_hs_times, plot_frame, i)
            plots.append(fig)
            continue

        df = gait_parameters(hs_selected_idx_new,to_selected_idx_new,df,i,walk_start,walk_end,cad,fs,fs_HS_TO)
        fig = linear_plot(time_vector, acc_ap_pp, acc_wave_detrended, acc_wave_2, hs_times, hs_selected_idx, to_times, to_selected_idx, invalid_hs_idx, invalid_hs_times, plot_frame, i)
        plots.append(fig)

    return df, plots

def nonlinear_analysis(filename, plot_frame, assume_walking=False):
    fs = 100 # sampling frequency of sensor

    accleration = pd.read_csv(filename)
    accleration['TgF'] = np.sqrt(accleration['Ax']**2+accleration['Ay']**2+accleration['Az']**2)
    R_acc = accleration['TgF'] - 1 #resultant acceleration adjusted with gravity
    vm = np.array(R_acc) #converting to numpy array

    # Resample the signal to 10 hz find_walking needs signal sampled at 10 hz
    fs_walking = 10 # sampling rate required by find_walking function
    num_samples = int(np.size(vm)*fs_walking/fs)
    vm_resample = resample(vm, num_samples)

    # For the function to work properly it needs the number of samples to be a multiple of frequency(10hz)
    # the function arranges the signal into matrix with each column containing 10 samples ie data for 1 second
    num_elements_to_use = (vm_resample.size // fs_walking) * fs_walking
    vm_bout = vm_resample[:num_elements_to_use]

    # parameters for find walking function
    min_amp = 0.3 # amplitude threshold (in g )
    T = 3 # minimum walking duration (in seconds)
    delta = 20 #maximum difference between consecutive peaks (in multiplication of 0.05Hz)
    alpha = 1.6 #maximum ratio between dominant peak below and within step frequency range
    beta = 2.5 # maximum ratio between dominant peak above and within step frequency range
    step_freq = (1.4,2.3) #step frequency range (in Hz or steps per second)

    fs_HS_TO = 100 #sampling frequency used for gait parameters and non linear analysis

    if assume_walking:
        walking = np.array([[0, len(vm) * fs_HS_TO // fs]])
    else:
        cad = find_walking(vm_bout, 10, min_amp, step_freq, alpha, beta, T, delta)
        walking = _walking_period_detection(cad, fs_HS_TO)
        print("cadence: ")
        print(cad)
        print(f"Walking periods found: {len(walking) if len(walking.shape) > 0 else 0}")

    if len(walking) > 0:
        for i, period in enumerate(walking):
            start_sec = period[0] / fs_HS_TO
            end_sec = period[1] / fs_HS_TO  
            duration = end_sec - start_sec
            print(f"  Period {i+1}: {start_sec:.1f}s to {end_sec:.1f}s ({duration:.1f}s duration)")
    else:
        print("  No walking periods detected!")

    if len(walking) == 0:
        print("No walking periods found. Returning empty results.")
        empty_df = pd.DataFrame(columns=['walking_index','start_index', 'end_index','delay','dimension','Ap_en','Samp_en','Sym_en',
                                'Permu_en','LyEl_R','LyEs_R','Lye_W','REC','DET','MeanL','MaxL',
                                'EntrL','LAM','MeanV','MaxV','EntrV','EntrW','RCMSE','CMSE','MSE','MSE_SCALE1','MSE_SCALE2'])
        return empty_df, []

    # Display the results
    print("Nonlinear Analysis: ")
    print("walking periods: ")
    print(walking)

    res_acc = R_acc+1 # acceleration in the anterior posterior directtion
    num_samples = int(len(res_acc) * fs_HS_TO / fs)  # Calculate the number of samples in the resampled signal

    #Resample the signal
    resampled_res_acc = resample(res_acc, num_samples)

    print("resampled_res_acc")
    print(resampled_res_acc)

    df2 = pd.DataFrame(columns=['walking_index','start_index', 'end_index','delay','dimension','Ap_en','Samp_en','Sym_en',
                            'Permu_en','LyEl_R','LyEs_R','Lye_W','REC','DET','MeanL','MaxL',
                            'EntrL','LAM','MeanV','MaxV','EntrV','EntrW','RCMSE','CMSE','MSE','MSE_SCALE1','MSE_SCALE2'])
    
    plots = []

    for i in range(len(walking)):
        print("iterating through walking. Index: ", i)
        walk_start = walking[i,0]
        walk_end= walking[i,1]
        data = resampled_res_acc[walk_start:walk_end]
        #Calculate delay from Stergiou
        tau, V_ami = AMI_Stergiou(data,35)
        print("AMI_Stergiou calculated")
        delay = int(tau[0][0])
        #Calculate dimensions from fnn
        # Parameters for fnn function
        MaxDim = 30
        Rtol = 15
        Atol = 2
        speed = 0
        ans = FNN(data, delay, MaxDim, Rtol, Atol, speed)
        print("FNN calculated")
        dim = ans[1]  #dimension
        # Approximate entropy
        r = 0.2 #tolerance
        AE = Ent_Ap(data, dim, r)
        print("ENT_AP calculated")
        # Sample Entropy
        m = 2 # - m is generally recommendation as 2
        #  - R is generally recommendation as 0.2
        Samp_Ent = Ent_Samp(data, m, r)
        print("ENT_Samp calculated")
        #Symbolic Entropy
        L = 2 #assuming
        #normalizing data
        data_normalized = (data - np.min(data)) / (np.max(data) - np.min(data))
        data_scaled = (data_normalized * 1.99).astype(int)
        Sym_En = Ent_Symbolic(data_scaled, L)
        print("ENT_Symbolic calculated")
        # Permutaion Entropy
        '''
        (permEnt, hist) = Ent_Permu20180320(data, m, tau)
        inputs -  data: 1-D array of data being analyzed
                m: embedding dimension (order of permutation entropy)
                tau: time delay
        outputs - permuEnt: value calculated using a log base of 2
                hist: number of occurences for each permutation order
        '''
        [permEnt_value,hist_value] = Ent_Permu(data, m, delay)
        print("ENT_Permu calculated")
        #LyE_Rosenstein
        name = "test"
        slope = [1,2,3,4]
        MeanPeriod = 1
        Plot = False
        (LyEl,LyEs,out), time, AveLnDiv, LyES, timeS, lyESline, LyEL, timeL, LyELline = LyE_R(data,name,fs_HS_TO,delay,m,slope, MeanPeriod, Plot)
        fig = nonlinear_plot(time, AveLnDiv, LyES, timeS, lyESline, LyEL, timeL, LyELline, plot_frame, i)
        print("nonlinear plot produced")
        plots.append(fig)
        print("LYE_R calculated")
        #largest lyapunov exponent
        evolve = 2 # assuming
        [out,lye] = LyE_W(data, fs_HS_TO, delay, dim, evolve)
        print("LYE_W calculated")
        # RQA
        TYPE = 'RQA'
        ZSCORE = 1
        NORM = 'NON'
        LINELENGTH = 1
        SETVALUE = 1
        SETPARA = 'radius'
        PLOTOPTION = 0
        column = "1"
        nargout =1
        rqa_RESULTS = RQA(data, TYPE ,dim,delay,ZSCORE,NORM,LINELENGTH,SETPARA,SETVALUE,PLOTOPTION, column, nargout)
        print("RQA calculated")
        REC=rqa_RESULTS[0]['REC']
        DET=rqa_RESULTS[0]['DET']
        MeanL= rqa_RESULTS[0]['MeanL']
        MaxL= rqa_RESULTS[0]['MaxL']
        EntrL= rqa_RESULTS[0]['EntrL']
        LAM= rqa_RESULTS[0]['LAM']
        MeanV= rqa_RESULTS[0]['MeanL']
        MaxV= rqa_RESULTS[0]['MaxV']
        EntrV=rqa_RESULTS[0]['EntrV']
        EntrW=rqa_RESULTS[0]['EntrW']

        tau = 20
        r = 0.2
        m=2

        result =  Ent_MS_Plus(data,tau, m, r )
        print("ENT_MS_Plus calculated")

        RCMSE =result[0]
        CMSE = result[1]
        MSE = result[2]
        # Initialize a list to store rows
        rows = []
        # change MSE to an array of 3 columns
        # Iterate through the array and build rows
        for item in MSE:
            if isinstance(item, tuple):
                rows.append(item)  # Append the tuple as is
            else:
                rows.append((item, np.nan, np.nan))  # Convert non-tuple items to (item, NaN, NaN)

        # Convert the list of rows to a NumPy array
        MSE = np.array(rows)
        # chnage the data type to float
        RCMSE = RCMSE.astype(float)
        CMSE = CMSE.astype(float)

        # Pad the single float value variable with nan values
        max_len = MSE.shape[0]

        lists = [i+1,walk_start,walk_end,delay,dim,AE,Samp_Ent,Sym_En,permEnt_value,LyEl,LyEs,lye,REC,DET,MeanL,MaxL,EntrL,LAM,MeanV,MaxV,EntrV,EntrW]
        padded_lists = []

        # Pad each variable
        for value in lists:
            # Convert scalar to array and pad
            value_array = np.array([value])
            value_array = value_array.astype(float)
            padded_array = np.pad(value_array, (0, max_len - len(value_array)), mode='constant', constant_values=np.nan)
            padded_lists.append(padded_array)

        # Convert list of padded arrays to a 2D NumPy array
        padded_lists = np.vstack(padded_lists)
        padded_lists = np.transpose(padded_lists)

        new_row = pd.DataFrame({'walking_index':padded_lists[:,0],'start_index':padded_lists[:,1], 'end_index':padded_lists[:,2],'delay':padded_lists[:,3],'dimension':padded_lists[:,4],'Ap_en':padded_lists[:,5],'Samp_en':padded_lists[:,6],'Sym_en':padded_lists[:,7],
                                'Permu_en':padded_lists[:,8],'LyEl_R':padded_lists[:,9],'LyEs_R':padded_lists[:,10],'Lye_W':padded_lists[:,11],'REC':padded_lists[:,12],'DET':padded_lists[:,13],'MeanL':padded_lists[:,14],'MaxL':padded_lists[:,15],
                                'EntrL':padded_lists[:,16],'LAM':padded_lists[:,17],'MeanV':padded_lists[:,18],'MaxV':padded_lists[:,19],'EntrV':padded_lists[:,20],'EntrW':padded_lists[:,21],'RCMSE':RCMSE,'CMSE':CMSE,'MSE':MSE[:,0],'MSE_SCALE1':MSE[:,1],'MSE_SCALE2':MSE[:,2]})

        df2 = pd.concat([df2, new_row], ignore_index=True)

    print("returning non-linear analysis")
    return df2, plots

def _walking_period_detection(cad, fs_HS_TO=100):
    wi = np.where(cad > 0, 1, 0)
    wi_resampled = np.repeat(wi, fs_HS_TO)
    
    if len(wi_resampled) == 0 or np.sum(wi) == 0:
        return np.array([]).reshape(0, 2)
    
    # Find internal transitions only
    change_indices = np.where(np.diff(wi_resampled) != 0)[0] + 1
    
    # Build start and stop indices separately
    start_indices = []
    stop_indices = []
    
    # Handle start boundary
    if wi_resampled[0] == 1:
        start_indices.append(0)
    
    # Process internal transitions
    for idx in change_indices:
        if wi_resampled[idx] == 1:  # Transition from 0 to 1 (start walking)
            start_indices.append(idx)
        else:  # Transition from 1 to 0 (stop walking)
            stop_indices.append(idx)
    
    # Handle end boundary
    if wi_resampled[-1] == 1:  # Walking continues to end
        stop_indices.append(len(wi_resampled))
    
    # Pairing them up
    walking_periods = []
    for i in range(len(start_indices)):
        if i < len(stop_indices):
            walking_periods.append([start_indices[i], stop_indices[i]])
    
    return np.array(walking_periods) if walking_periods else np.array([]).reshape(0, 2)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt