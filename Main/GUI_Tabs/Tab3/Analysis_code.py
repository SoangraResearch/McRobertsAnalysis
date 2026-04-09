import copy
import os
from typing import Any, Dict, Optional

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import resample
# nonlinear_plot moved to Tab3Controller — plots must be built on the main thread
from Main import app_config
from Main.GUI_Tabs.Tab3.Analysis_Plots import linear_plot
from Main.GUI_Tabs.Tab3.nonlinear_progress_instrument import NonlinearProgressInstrument
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

SettingsDict = Dict[str, Any]


def _settings_copy(settings: Optional[SettingsDict] = None) -> SettingsDict:
    """Snapshot of effective settings (``app_config.current`` when ``settings`` is None)."""
    return copy.deepcopy(app_config.current if settings is None else settings)


def linear_analysis(
    filename,
    plot_frame=None,
    assume_walking=False,
    build_plots=True,
    embed_plots=True,
    settings=None,
):
    """Linear gait analysis.

    If build_plots is True, plot_frame must be set when embed_plots is True so figures
    can be embedded in the GUI. If embed_plots is False, only Figure objects are
    returned (e.g. before display_combined_plots with nonlinear results).
    If build_plots is False (e.g. Tab 4 batch), returns (df, list[dict]) for linear_plot
    payloads; plots are discarded by callers that only need the dataframe.

    Args:
        settings: Optional nested settings dict; defaults to :data:`Main.app_config.current`.
    """
    cfg = _settings_copy(settings)
    wcfg = cfg["walking"]

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
    min_amp = wcfg["min_amp"]
    T = wcfg["min_duration_s"]
    delta = wcfg["delta"]
    alpha = wcfg["alpha"]
    beta = wcfg["beta"]
    step_freq = (wcfg["step_freq_low"], wcfg["step_freq_high"])
    wavelet_straight = wcfg["wavelet_type_straight"]
    wavelet_turning = wcfg["wavelet_type_turning"]

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

    n_walk = len(walking)
    for i in range(n_walk):
        walk_start = walking[i,0]
        walk_end= walking[i,1]
        walk = resampled_az[walk_start:walk_end]

        # Get heal strike and toe off
        hs_selected_idx, to_selected_idx, invalid_hs_idx, time_vector, acc_ap_pp, acc_wave_detrended, acc_wave_2, hs_times, to_times, invalid_hs_times = get_hs_to_wavelet(
            walk,
            fs_HS_TO,
            turning,
            0,
            "No plot name",
            wavelet_type_straight=wavelet_straight,
            wavelet_type_turning=wavelet_turning,
        )
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
            if build_plots:
                fig = linear_plot(
                    time_vector,
                    acc_ap_pp,
                    acc_wave_detrended,
                    acc_wave_2,
                    hs_times,
                    hs_selected_idx,
                    to_times,
                    to_selected_idx,
                    invalid_hs_idx,
                    invalid_hs_times,
                    plot_frame,
                    i,
                    embed=embed_plots,
                )
                plots.append(fig)
            else:
                plots.append(
                    _linear_plot_payload(
                        i,
                        time_vector,
                        acc_ap_pp,
                        acc_wave_detrended,
                        acc_wave_2,
                        hs_times,
                        hs_selected_idx,
                        to_times,
                        to_selected_idx,
                        invalid_hs_idx,
                        invalid_hs_times,
                    )
                )
            continue

        df = gait_parameters(hs_selected_idx_new,to_selected_idx_new,df,i,walk_start,walk_end,cad,fs,fs_HS_TO)
        if build_plots:
            fig = linear_plot(
                time_vector,
                acc_ap_pp,
                acc_wave_detrended,
                acc_wave_2,
                hs_times,
                hs_selected_idx,
                to_times,
                to_selected_idx,
                invalid_hs_idx,
                invalid_hs_times,
                plot_frame,
                i,
                embed=embed_plots,
            )
            plots.append(fig)
        else:
            plots.append(
                _linear_plot_payload(
                    i,
                    time_vector,
                    acc_ap_pp,
                    acc_wave_detrended,
                    acc_wave_2,
                    hs_times,
                    hs_selected_idx,
                    to_times,
                    to_selected_idx,
                    invalid_hs_idx,
                    invalid_hs_times,
                )
            )

    return df, plots


def _linear_plot_payload(
    plot_num,
    time_vector,
    acc_ap_pp,
    acc_wave_detrended,
    acc_wave_2,
    hs_times,
    hs_selected_idx,
    to_times,
    to_selected_idx,
    invalid_hs_idx,
    invalid_hs_times,
):
    return {
        "plot_num": plot_num,
        "time_vector": time_vector,
        "acc_ap_pp": acc_ap_pp,
        "acc_wave_detrended": acc_wave_detrended,
        "acc_wave_2": acc_wave_2,
        "hs_times": hs_times,
        "hs_selected_idx": hs_selected_idx,
        "to_times": to_times,
        "to_selected_idx": to_selected_idx,
        "invalid_hs_idx": invalid_hs_idx,
        "invalid_hs_times": invalid_hs_times,
    }

def nonlinear_analysis(
    filename,
    assume_walking=False,
    progress_callback=None,
    progress_instrument: Optional[NonlinearProgressInstrument] = None,
    settings=None,
):
    """Runs nonlinear analysis on a background thread.

    Returns raw plot data (dicts) instead of Matplotlib figures, because
    Tkinter widgets can only be created on the main thread. The caller
    (Tab3Controller) converts these dicts into figures after this returns.

    Args:
        filename: Path to CSV with acceleration data (Ax, Ay, Az).
        assume_walking: If True, treats the entire file as one walking period.
        progress_callback: Optional function(str) for live GUI status updates.
        progress_instrument: Optional recorder that forwards messages to the GUI
            callback and logs timed events for ETA (see
            :class:`NonlinearProgressInstrument`). When set, ``progress_callback``
            is ignored for messages emitted via the instrument.
        settings: Optional settings dict (defaults to :data:`Main.app_config.current`).

    Returns:
        (DataFrame, list[dict]): Results table and raw LyE plot data per period.
    """
    cfg = _settings_copy(settings)
    if progress_instrument is not None:
        progress_instrument.mark_run_start()

    def _notify(msg: str) -> None:
        if progress_instrument is not None:
            progress_instrument.notify(msg)
        elif progress_callback is not None:
            progress_callback(msg)
    wcfg = cfg["walking"]
    ps = cfg["phase_space"]
    ent = cfg["entropy"]
    ly = cfg["lyapunov"]
    rq = cfg["rqa"]

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
    min_amp = wcfg["min_amp"]
    T = wcfg["min_duration_s"]
    delta = wcfg["delta"]
    alpha = wcfg["alpha"]
    beta = wcfg["beta"]
    step_freq = (wcfg["step_freq_low"], wcfg["step_freq_high"])

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
        if progress_instrument is not None:
            progress_instrument.mark_bouts_resolved(
                num_periods=0,
                assume_walking=assume_walking,
                total_resampled_samples=0,
                total_walking_samples=0,
            )
        empty_df = pd.DataFrame(columns=['walking_index','start_index', 'end_index','delay','dimension','Ap_en','Samp_en','Sym_en',
                                'Permu_en','LyEl_R','LyEs_R','Lye_W','REC','DET','MeanL','MaxL',
                                'EntrL','LAM','MeanV','MaxV','EntrV','EntrW','RCMSE','CMSE','MSE','MSE_SCALE1','MSE_SCALE2'])
        if progress_instrument is not None and os.environ.get(
            "MCROBERTS_DEBUG_NONLINEAR_TIMING"
        ):
            print(progress_instrument.summary_line())
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

    num_periods = len(walking)
    total_walking_samples = int(
        sum(int(walking[j, 1]) - int(walking[j, 0]) for j in range(num_periods))
    )
    if progress_instrument is not None:
        progress_instrument.mark_bouts_resolved(
            num_periods=num_periods,
            assume_walking=assume_walking,
            total_resampled_samples=int(len(resampled_res_acc)),
            total_walking_samples=total_walking_samples,
        )

    for i in range(num_periods):
        print("iterating through walking. Index: ", i)
        walk_start = walking[i,0]
        walk_end= walking[i,1]
        data = resampled_res_acc[walk_start:walk_end]

        if progress_instrument is not None:
            progress_instrument.mark_bout_start(i, num_periods, int(len(data)))

        _notify(f"Period {i+1}/{num_periods}: Computing AMI...")
        #Calculate delay from Stergiou
        tau, V_ami = AMI_Stergiou(data, int(ps["ami_max_lag"]))
        print("AMI_Stergiou calculated")
        delay = int(tau[0][0])
        _notify(f"Period {i+1}/{num_periods}: Computing FNN...")
        #Calculate dimensions from fnn
        # Parameters for fnn function
        MaxDim = int(ps["fnn_max_dim"])
        Rtol = int(ps["fnn_rtol"])
        Atol = int(ps["fnn_atol"])
        speed = float(ps["fnn_speed"])
        ans = FNN(data, delay, MaxDim, Rtol, Atol, speed)
        print("FNN calculated")
        dim = ans[1]  #dimension
        _notify(f"Period {i+1}/{num_periods}: Computing entropies...")
        # Approximate entropy
        r = float(ent["r"])
        AE = Ent_Ap(data, dim, r)
        print("ENT_AP calculated")
        # Sample Entropy
        m = int(ent["m"])
        Samp_Ent = Ent_Samp(data, m, r)
        print("ENT_Samp calculated")
        #Symbolic Entropy
        L = int(ent["symbolic_L"])
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
        _notify(f"Period {i+1}/{num_periods}: Computing LyE_R...")
        #LyE_Rosenstein
        name = "test"
        slope = [int(x) for x in ly["rosenstein_slope_periods"]]
        MeanPeriod = int(ly["rosenstein_mean_period"])
        Plot = False
        # Use dim (FNN-determined embedding dimension), not m (entropy param which is always 2)
        (LyEl,LyEs,out), time, AveLnDiv, LyES, timeS, lyESline, LyEL, timeL, LyELline = LyE_R(data,name,fs_HS_TO,delay,dim,slope, MeanPeriod, Plot)
        print("LYE_R calculated")
        # Store raw plot data — figures are built on the main thread by Tab3Controller
        plot_data = {
            'time': time, 'AveLnDiv': AveLnDiv,
            'LyES': LyES, 'timeS': timeS, 'lyESline': lyESline,
            'LyEL': LyEL, 'timeL': timeL, 'LyELline': LyELline
        }
        plots.append(plot_data)
        _notify(f"Period {i+1}/{num_periods}: Computing LyE_W...")
        #largest lyapunov exponent
        evolve = int(ly["wolf_evolve"])
        [out,lye] = LyE_W(data, fs_HS_TO, delay, dim, evolve)
        print("LYE_W calculated")
        _notify(f"Period {i+1}/{num_periods}: Computing RQA...")
        # RQA
        TYPE = 'RQA'
        ZSCORE = int(rq["zscore"])
        NORM = str(rq["norm"])
        LINELENGTH = int(rq["line_length"])
        SETVALUE = float(rq["set_value"])
        SETPARA = str(rq["set_para"])
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

        _notify(f"Period {i+1}/{num_periods}: Computing MSE...")

        mse_scale = int(ent["mse_max_scale"])
        r_mse = float(ent["r"])
        m_mse = int(ent["m"])

        result = Ent_MS_Plus(data, mse_scale, m_mse, r_mse)
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

        if progress_instrument is not None:
            progress_instrument.mark_bout_end(i, num_periods)

    if progress_instrument is not None and os.environ.get(
        "MCROBERTS_DEBUG_NONLINEAR_TIMING"
    ):
        print(progress_instrument.summary_line())

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
