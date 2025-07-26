import os
import csv
import tkinter as tk
import pandas as pd
import numpy as np
from datetime import timedelta, datetime
from tkinter import filedialog, messagebox, ttk
import matplotlib.dates as mdates
from Main.ICDA_code import step_detection
from Main.OMX_To_CSV import process_omx_file, matlab_datenum_to_datetime
from Main.Acceleration_Plot import PlotOMX
from Main.GSD_plots import plot_GSDA, plot_GSDB, plot_steps

#setting directory properly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# -------------------------Tkinter Setup---------------------------------

# Create the main window
root = tk.Tk()
root.title("McRoberts Analysis")
root.geometry("1000x600")

tab_control = ttk.Notebook(root)
tab1 = tk.Frame(tab_control)
tab2 = tk.Frame(tab_control)
tab_control.add(tab1, text="Select Data")
tab_control.add(tab2, text="Mobilise-D")

tab_control.pack(expand=1, fill='both')

plot_frame_OMX = None
acceleration_plot = None
mobiliseD_file = None
exported_csv_path = "None"
start_time_var = tk.StringVar()
stop_time_var = tk.StringVar()
file_start_time_var = tk.StringVar()
file_stop_time_var = tk.StringVar()
label_var = tk.StringVar()
export_format_var = tk.StringVar()

# -------------------------Tab 1 Methods---------------------------------
def update_time_vars():
    if acceleration_plot is not None:
        start_dt, stop_dt = acceleration_plot.get_current_bounds()
        start_time_var.set(start_dt.strftime('%Y-%m-%d %H:%M:%S'))
        stop_time_var.set(stop_dt.strftime('%Y-%m-%d %H:%M:%S'))

def on_time_var_changed(*args):
    if acceleration_plot is not None:
        start_val = start_time_var.get()
        stop_val = stop_time_var.get()

        if not start_val or not stop_val:
            return

        start_dt = datetime.strptime(start_val, '%Y-%m-%d %H:%M:%S')
        stop_dt = datetime.strptime(stop_val, '%Y-%m-%d %H:%M:%S')
        
        start_num = mdates.date2num(start_dt)
        stop_num = mdates.date2num(stop_dt)

        acceleration_plot.zoom_to_bounds(start_num, stop_num)

def load_file():
    global data, filename, acceleration_plot

    file_path = filedialog.askopenfilename(filetypes=[("OMX file", "*.OMX")])
    if not file_path:
        return
    
    selected_file = file_path

    data, filename = process_omx_file(selected_file)

    acceleration_plot = PlotOMX(data, filename, plot_frame_OMX)
    update_time_vars()

    start_dt, stop_dt = acceleration_plot.get_current_bounds()
    file_start_time_var.set(start_dt.strftime('%Y-%m-%d %H:%M:%S'))
    file_stop_time_var.set(stop_dt.strftime('%Y-%m-%d %H:%M:%S'))

    acceleration_plot.register_view_change_callback(update_time_vars)

def load_time_entries():
    # Outer frame to hold both pairs horizontally
    time_frame = tk.Frame(tab1)
    time_frame.pack(pady=10)

    # Start time group
    start_group = tk.Frame(time_frame)
    start_group.pack(side="left", padx=40)

    tk.Label(start_group, text="File Start Time:", width=32, anchor='center').pack()
    tk.Entry(start_group, textvariable=file_start_time_var, state='readonly', width=20).pack()

    # Stop time group
    stop_group = tk.Frame(time_frame)
    stop_group.pack(side="left", padx=40)

    tk.Label(stop_group, text="File Stop Time:", width=32, anchor='center').pack()
    tk.Entry(stop_group, textvariable=file_stop_time_var, state='readonly', width=20).pack()

    # Outer frame to hold both start and stop time groups horizontally
    time_frame = tk.Frame(tab1)
    time_frame.pack(pady=10)

    # Start time group
    start_group = tk.Frame(time_frame)
    start_group.pack(side="left", padx=40)

    tk.Label(start_group, text="Start Time (YYYY-MM-DD HH:MM:SS):", width=32, anchor='w').pack()
    start_entry = tk.Entry(start_group, textvariable=start_time_var)
    start_entry.pack()

    # Stop time group
    stop_group = tk.Frame(time_frame)
    stop_group.pack(side="left", padx=40)

    tk.Label(stop_group, text="Stop Time (YYYY-MM-DD HH:MM:SS):", width=32, anchor='w').pack()
    stop_entry = tk.Entry(stop_group, textvariable=stop_time_var)
    stop_entry.pack()

    start_time_var.trace_add("write", on_time_var_changed)
    stop_time_var.trace_add("write", on_time_var_changed)

def export_csv():
    global mobiliseD_file
    safe_start = start_time_var.get().replace(":", "-").replace(" ", "_")
    safe_stop = stop_time_var.get().replace(":", "-").replace(" ", "_")

    export_folder = os.path.join(os.getcwd(), "../Data/Output/" + filename)
    os.makedirs(export_folder, exist_ok=True)

    output_path=filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        initialdir=export_folder,
        initialfile=filename + "_from_" + safe_start + "_to_" + safe_stop + ".csv",
        title="Save CSV File"
    )

    if not output_path:
        return False

    starttime = datetime.strptime(start_time_var.get(), "%Y-%m-%d %H:%M:%S")
    stoptime = datetime.strptime(stop_time_var.get(), "%Y-%m-%d %H:%M:%S")

    try:
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow(['Time', 'Ax', 'Ay', 'Az'])
            for row in data['ACC']:
                ts = matlab_datenum_to_datetime(row[0])
                if starttime <= ts <= stoptime:
                    writer.writerow(row)
            messagebox.showinfo("Success", f"File saved to:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save file: {e}")
        return False
    
    mobiliseD_file = output_path
    mobilised_path_var.set(f"File loaded: {mobiliseD_file}")
    
# -------------------------Tab 2 Methods---------------------------------
def load_mobiliseD_file():
    global mobiliseD_file
    file_path = filedialog.askopenfilename(filetypes=[("CSV/JSON files", "*.csv *.json")])
    if not file_path:
        return
    try:
        if file_path.endswith(".csv"):
            messagebox.showinfo("Loaded", f"Loaded file:\n{file_path}")
            mobiliseD_file = file_path
            mobilised_path_var.set(f"File loaded: {mobiliseD_file}")
        else:
            raise ValueError("Unsupported file format")
    except Exception as e:
        messagebox.showerror("Load Error", str(e))

def convert_mobiliseD_file_to_df():
    global mobiliseD_file, mobiliseD_df
    try:
        mobiliseD_df = pd.read_csv(mobiliseD_file)
    except Exception as e:
        messagebox.showerror("Load Error", str(e))

def process_GSD():
    global mobiliseD_df, gsd_result
    convert_mobiliseD_file_to_df()

    try:
        acc = mobiliseD_df.iloc[:, 1:4].to_numpy()
        time_col = mobiliseD_df['Time'].to_numpy()
        original_time_array = [matlab_datenum_to_datetime(t) for t in time_col]
        fs = 100
        print(label_var_MobiliseD.get())
        if label_var_MobiliseD.get() == "Healthy(GSDA)":
            from Main.GSDA_code import gsd_iluz
            imu_input = {"LowerBack": {"Acc": acc, "Gyr": np.zeros_like(acc), "Fs": {"Acc": fs}}}
            gsd_result, gait_bool_for_plot, v_acc_for_plot = gsd_iluz(imu_input, time_vector=original_time_array, plot_results=False)
            plot_GSDA(gait_bool_for_plot, v_acc_for_plot, plot_left_GSD)
        elif label_var_MobiliseD.get() == "Patient(GSDB)":
            from Main.GSDB_code import gsd_low_back_acc
            gsd_result, sig_det_act_for_plot, walk_label_for_plot = gsd_low_back_acc(acc, fs, plot_results=False, time_vector=original_time_array)
            plot_GSDB(sig_det_act_for_plot, walk_label_for_plot, plot_left_GSD)
        else:
            gsd_result = -1
        sd_result_df = pd.DataFrame(gsd_result)
        step_result= step_detection(acc, gsd_result, fs, plot_results=False)
        plot_steps(gsd_result, fs, v_acc_for_plot, plot_right_GSD)
        messagebox.showinfo("GSD Result", f"Gait sequences found: {len(gsd_result)}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    
    #TODO: plot steps
    #TODO: save data

# -------------------------Tab 1 Select Data---------------------------------

load_file_button = tk.Button(tab1, text="Load OMX File", command=load_file)
load_file_button.pack(pady=10)

plot_frame_OMX = tk.Frame(tab1, height=350)
plot_frame_OMX.pack_propagate(False)

load_time_entries()

plot_frame_OMX.pack(fill="both", expand=True)

button_frame = tk.Frame(tab1)
button_frame.pack(pady=10)

Export_Button = tk.Button(button_frame, text="Export To CSV", command=export_csv)
Export_Button.pack()

# -------------------------Tab 2 Mobilise D---------------------------------
tk.Button(tab2, text="Upload CSV File", command=load_mobiliseD_file).pack(pady=10)

mobilised_path_var = tk.StringVar(value="File loaded: (none)")
MobiliseD_file_label = tk.Label(tab2, textvariable=mobilised_path_var)
MobiliseD_file_label.pack()

label_var_MobiliseD = tk.StringVar()
label_var_MobiliseD.set("None")
tk.Label(tab2, text="Select Type").pack(pady=(20, 5))
label_frame = tk.Frame(tab2)
label_frame.pack()
for lbl in ["Healthy(GSDA)", "Patient(GSDB)"]:
    tk.Radiobutton(label_frame, text=lbl, variable=label_var_MobiliseD, value=lbl).pack(side="left", padx=20)

tk.Button(tab2, text="Run GSD Detection", command=process_GSD).pack(pady=15)

plot_frame_GSD = tk.Frame(tab2, height=300)
plot_frame_GSD.pack(fill="both", expand=True)

# Left and right frames inside plot_frame_GSD
plot_left_GSD = tk.Frame(plot_frame_GSD, width=500)
plot_left_GSD.pack(side='left', fill='both', expand=True)

plot_right_GSD = tk.Frame(plot_frame_GSD, width=500)
plot_right_GSD.pack(side='left', fill='both', expand=True)

# Create a frame to hold the buttons horizontally
button_frame = tk.Frame(tab2)
button_frame.pack(pady=5)

# Add buttons side by side
tk.Button(button_frame, text="Save GSD Result", command=None).pack(side="left", padx=5)
tk.Button(button_frame, text="Save GSD plot", command=None).pack(side="left", padx=5)
tk.Button(button_frame, text="Save Step Counts", command=None).pack(side="left", padx=5)
tk.Button(button_frame, text="Save Steps plot", command=None).pack(side="left", padx=5)

tk.Button(tab2, text="Save All", command=None).pack(pady=5)

# -------------------------Running the GUI---------------------------------
root.mainloop()