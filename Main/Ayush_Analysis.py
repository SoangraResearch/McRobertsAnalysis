import pandas as pd
import numpy as np
from scipy.signal import resample
from Non_GUI.Ayush_Files.gait_functions.walking import find_walking

def linear_analysis(file):
    fs = 500 # sampling frequency of sensor

    accleration = pd.read_csv(file)
    accleration['TgF'] = np.sqrt(accleration['Ax']**2+accleration['Ay']**2+accleration['Az']**2)
    R_acc = accleration['TgF'] - 1 #resultant acceleration adjusted with gravity
    vm = np.array(R_acc) #converting to numpy array

    ## Parameters for find_walking and get_hs_to_wavelet function
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

    # heal strike toe off detection
    fs_HS_TO = 100 #sampling frequency needed by the function
    turning = 0
    plot_figure = 1 # 1 for plotting the figure
    save_fig_name = "TestData_Image"

    cad = find_walking(vm_bout, 10, min_amp,step_freq, alpha, beta, T,delta)
