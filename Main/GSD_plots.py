import os
import sys
import pywt
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import filtfilt
from scipy.io import loadmat
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from GSDB_code import resamp_interp

def plot_GSDA(gait_bool, v_acc, plot_frame):
    for w in plot_frame.winfo_children():
        w.destroy()

    # build the figure
    fig = Figure(figsize=(3.5, 3), dpi=100)
    ax = fig.add_subplot(111)

    ax.plot(v_acc, label='Vertical Acc')
    ax.plot(gait_bool * np.max(v_acc), label='Detected Gait')
    ax.set_xlabel('Samples')
    ax.set_ylabel('Value')
    ax.set_title("Gait Sequence Detection (GSDA)")
    ax.legend()
    fig.tight_layout()

    # embed into Tk frame
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

    return fig

def plot_GSDB(sig_det_actv, walk_label, plot_frame):
    for w in plot_frame.winfo_children():
        w.destroy()
    
    # build the figure
    fig = Figure(figsize=(3.5, 3), dpi=100)
    ax = fig.add_subplot(111)
    
    # Create time axis for proper scaling
    time_axis = np.arange(len(sig_det_actv)) / 40.0  # 40Hz sampling rate
    
    ax.plot(time_axis, sig_det_actv, label='filtered accNorm')
    ax.plot(time_axis, walk_label, 'r', linewidth=2, label='Walking')
    ax.set_xlabel('Time (seconds)')
    ax.set_title("Gait Sequence Detection (GSDB)")
    ax.legend()
    fig.tight_layout()
    
    # embed into Tk frame
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)
    
    return fig

def plot_steps(GS, fs, acc_v, plot_frame):
    # .app support: use bundled path when running as .app
    if getattr(sys, 'frozen', False):
        mat_file_path = os.path.join(sys._MEIPASS, "Mobilise-D-TVS-Recommended-Algorithms-master", "ICDA", "Library", "FIR-2-3Hz-40.mat")
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        mat_file_path = os.path.normpath(os.path.join(current_dir, "../Mobilise-D-TVS-Recommended-Algorithms-master/ICDA/Library/FIR-2-3Hz-40.mat"))
    Num = loadmat(mat_file_path)['Num'].flatten()

    fs_algo = 40
    IC_all_sig = np.concatenate([np.array(g['IC']) for g in GS if 'IC' in g and len(g['IC']) > 0])
    ICs = np.round(IC_all_sig * fs).astype(int)

    acc_v_40 = resamp_interp(acc_v, fs, fs_algo)
    acc_v_lpf = filtfilt(Num, [1], _remove_drift_40hz(acc_v_40))
    acc_v_lpf_int = np.cumsum(acc_v_lpf) / fs_algo
    acc_v_lpf_cwt, _ = pywt.cwt(acc_v_lpf_int, 9, 'gaus2', sampling_period=1 / fs_algo)
    acc_v_lpf_cwt = acc_v_lpf_cwt[0] - np.mean(acc_v_lpf_cwt[0])
    acc_v_processed = resamp_interp(acc_v_lpf_cwt, fs_algo, fs)

    # plotting
    for w in plot_frame.winfo_children():
        w.destroy()

    # build the figure
    fig = Figure(figsize=(3.5, 3), dpi=100)
    ax = fig.add_subplot(111)

    ax.plot(np.arange(len(acc_v_processed)), acc_v_processed, 'b', label='accV (processed)')
    ax.plot(ICs, acc_v_processed[ICs], 'ro', label='Initial Contacts (IC)')
    ax.legend()
    ax.set_title("Step Detection")
    ax.set_xlabel("Samples")
    fig.tight_layout()

    # embed into tk frame
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

    return fig

def _remove_drift_40hz(x):
    return filtfilt([1, -1], [1, -0.9748], x)