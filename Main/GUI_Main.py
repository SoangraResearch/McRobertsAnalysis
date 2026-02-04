import os
import tkinter as tk
import pandas as pd
import numpy as np
from tkinter import filedialog, messagebox, ttk
from ICDA_code import step_detection, filter_and_print_long_segments
from OMX_To_CSV import process_omx_file, matlab_datenum_to_datetime
from GSDA_code import gsd_iluz
from GSDB_code import gsd_low_back_acc
from auto_analysis_progress import auto_analysis_progress
from Auto_analysis_code import split_data_by_day

from GUI_Tabs.Tab1Controller import Tab1Controller
from GUI_Tabs.Tab2Controller import Tab2Controller
from GUI_Tabs.Tab3Controller import Tab3Controller

#setting directory properly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# -------------------------Tkinter Setup---------------------------------

# Create the main window
root = tk.Tk()
root.title("McRoberts Analysis")
root.geometry("1000x600")

tab_control = ttk.Notebook(root)

tab1 = tk.Frame(tab_control)
tab1_controller = Tab1Controller(tab1)
tab_control.add(tab1, text="Select Data")

tab2 = tk.Frame(tab_control)
tab2_controller = Tab2Controller(tab2)
tab_control.add(tab2, text="Mobilise-D")

tab3 = tk.Frame(tab_control)
tab3_controller = Tab3Controller(tab3)
tab_control.add(tab3, text="Ayush's Code")

tab4 = tk.Frame(tab_control)
tab_control.add(tab4, text="Auto-Analysis (WIP)")

tab_control.pack(expand=1, fill='both')

plot_frame_OMX = None
acceleration_plot = None
mobiliseD_file = None
mobiliseD_directory_path = None
mobilised_path_var = tk.StringVar()
ayush_code_path_var = tk.StringVar()
linear_plots = None
nonlinear_plots = None
exported_csv_path = "None"
start_time_var = tk.StringVar()
stop_time_var = tk.StringVar()
file_start_time_var = tk.StringVar()
file_stop_time_var = tk.StringVar()
label_var = tk.StringVar()
export_format_var = tk.StringVar()

auto_analysis_file = "None"

# -------------------------Tab 1 Methods---------------------------------

def export_csv():
    tab1_controller.export_csv()
    mobilised_path_var.set(f"File loaded: {tab1_controller.export_filename}")
    tab2_controller.set_file(os.path.join(tab1_controller.export_folder, tab1_controller.export_filename + ".csv"))
    ayush_code_path_var.set(f"File loaded: {tab1_controller.export_filename}")
    tab3_controller.set_file(os.path.join(tab1_controller.export_folder, tab1_controller.export_filename + ".csv"))
    
# -------------------------Tab 1 Select Data---------------------------------

load_file_button = tk.Button(tab1, text="Load OMX File", command=lambda: tab1_controller.load_file(plot_frame_OMX))
load_file_button.pack(pady=10)

plot_frame_OMX = tk.Frame(tab1, height=350)
plot_frame_OMX.pack_propagate(False)

tab1_controller.create_time_labels()

plot_frame_OMX.pack(fill="both", expand=True)

button_frame = tk.Frame(tab1)
button_frame.pack(pady=10)

Export_Button = tk.Button(button_frame, text="Export To CSV", command=lambda: export_csv())
Export_Button.pack(side="left", padx=5)

Export_Button = tk.Button(button_frame, text="Export Plot", command=lambda: tab1_controller.export_acceleration_plot())
Export_Button.pack(side="left", padx=5)

# -------------------------Tab 2 Methods---------------------------------

def load_mobiliseD_file():
    mobilised_path_var.set(tab2_controller.load_file())

# -------------------------Tab 2 Mobilise D---------------------------------

tk.Button(tab2, text="Load CSV File", command=lambda: load_mobiliseD_file()).pack(pady=10)

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

# container frame for button + checkbox
gsd_frame = tk.Frame(tab2)
gsd_frame.pack(pady=15)

# button
tk.Button(gsd_frame, text="Run GSD Detection", command=lambda: tab2_controller.process_GSD(label_var_MobiliseD.get(), force_data_as_walking.get(), plot_left_GSD, plot_right_GSD)).pack(side="left", padx=10)

# checkbox
force_data_as_walking = tk.BooleanVar(value=False)
tk.Checkbutton(gsd_frame, text="Force Data as Walking",
               variable=force_data_as_walking).pack(side="left", padx=10)

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
tk.Button(button_frame, text="Save GSD Result", command=lambda: tab2_controller.save_GSD_results(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save GSD plot", command=lambda: tab2_controller.save_GSD_plot(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save Step Counts", command=lambda: tab2_controller.save_step_counts(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save Steps plot", command=lambda: tab2_controller.save_steps_plot(True)).pack(side="left", padx=5)

tk.Button(tab2, text="Save All", command=lambda: tab2_controller.save_all_GSD()).pack(pady=5)

# -------------------------Tab 3 Methods---------------------------------

def load_ayush_code_file():
    ayush_code_path_var.set(tab3_controller.load_file())

# -------------------------Tab 3 Ayush's Code---------------------------------

tk.Button(tab3, text="Load CSV File", command=load_ayush_code_file).pack(pady=10)

ayush_code_path_var = tk.StringVar(value="File loaded: (none)")
ayush_code_file_label = tk.Label(tab3, textvariable=ayush_code_path_var)
ayush_code_file_label.pack()

analysis_frame = tk.Frame(tab3)
analysis_frame.pack(pady=5)

assume_walking_var = tk.BooleanVar(value=False)
plot_frame_ayush_code = tk.Frame(tab3, height=300)

tk.Button(analysis_frame, text="Linear Analysis", width=15, command=lambda: tab3_controller.do_linear_analysis(plot_frame_ayush_code, assume_walking_var)).pack(side="left", padx=10)
tk.Button(analysis_frame, text="Non-Linear Analysis", width=15, command=lambda: tab3_controller.do_nonlinear_analysis(plot_frame_ayush_code, assume_walking_var)).pack(side="left", padx=10)

tk.Checkbutton(analysis_frame, text="Assume data is walking", variable=assume_walking_var).pack(side="left", padx=10)

plot_frame_ayush_code.pack(fill="both", expand=True)

button_frame = tk.Frame(tab3)
button_frame.pack(pady=5)

tk.Button(button_frame, text="Save Linear Analysis", command=lambda: tab3_controller.save_linear_analysis(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save Non-Linear Analysis", command=lambda: tab3_controller.save_nonlinear_analysis(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save All Linear Analysis Plots", command=lambda: tab3_controller.save_all_linear_analysis_plots(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save All Non-Linear Analysis Plots", command=lambda: tab3_controller.save_all_nonlinear_analysis_plots(True)).pack(side="left", padx=5)

tk.Button(tab3, text="Save All", command=lambda: tab3_controller.save_all_output()).pack(pady=5)

# -------------------------Tab 4 Methods---------------------------------
def load_auto_analysis_file():
    global auto_analysis_file
    file_path = filedialog.askopenfilename(filetypes=[("OMX file", "*.OMX")])
    if not file_path:
        return
    
    auto_analysis_input_file = file_path

    if not file_path:
        return
    auto_analysis_directory_path = os.path.dirname(file_path)
    auto_analysis_filename = os.path.splitext(os.path.basename(file_path))[0]
    try:
        if file_path.endswith(".OMX"):
            messagebox.showinfo("Loaded", f"Loaded file:\n{file_path}")
            auto_analysis_file = file_path
            auto_analysis_path_var.set(f"File loaded: {auto_analysis_filename}")
        else:
            raise ValueError("Unsupported file format")
            auto_analysis_input_file = "None"
    except Exception as e:
        messagebox.showerror("Load Error", str(e))
        auto_analysis_input_file = "None"

def run_auto_analysis():
    global auto_analysis_file
    if (auto_analysis_file == "None"):
        messagebox.showerror("Error", "File not loaded")
        return

    if (label_var_auto_analysis.get() == "None"):
        messagebox.showerror("Error", "GSD algorithm not set")
        return
    
    progress_text.clear()

    progress_text.update_progress("Reading Data")

    auto_analysis_data, filename = process_omx_file(auto_analysis_file)

    # extract raw datenum timestamps
    timestamps = auto_analysis_data['ACC'][:, 0]

    progress_text.update_progress("Splitting Data")

    data_chunks = split_data_by_day(auto_analysis_data, timestamps)
    print("data chunks count: " + str(len(data_chunks)))

    progress_text.update_progress("Sequence Detection")

    #Running gsd algorithm
    for chunk in data_chunks:
        acc = chunk.iloc[:, 1:4].to_numpy()
        time_col = chunk['Time'].to_numpy()
        original_time_array = [matlab_datenum_to_datetime(t) for t in time_col]
        fs = 100
        if (label_var_auto_analysis).get() == "Healthy(GSDA)":
            imu_input = {"LowerBack": {"Acc": acc, "Gyr": np.zeros_like(acc), "Fs": {"Acc": fs}}}
            gsd_result, gait_bool_for_plot, v_acc_for_plot = gsd_iluz(imu_input, time_vector=original_time_array, plot_results=False, force_walking=False)
        elif (label_var_auto_analysis).get() == "Patient(GSDB)":
            gsd_result, sig_det_act_for_plot, walk_label_for_plot = gsd_low_back_acc(acc, fs, plot_results=False, time_vector=original_time_array, force_walking=force_data_as_walking.get())
        else:
            print("No data type selected!")
        long_segments = filter_and_print_long_segments(gsd_result, original_time_array=original_time_array)
        sd_result_df = pd.DataFrame(gsd_result)
        step_result = step_detection(acc, gsd_result, fs, plot_results=False, original_time_array=original_time_array)
        print("Long segments:", long_segments)

    progress_text.update_progress("Segment Selection")

# -------------------------Tab 4 Auto Analysis---------------------------------
load_file_button = tk.Button(tab4, text="Load OMX File", command=load_auto_analysis_file)
load_file_button.pack(pady=10)

auto_analysis_path_var = tk.StringVar(value="File loaded: (none)")
auto_analysis_file_label = tk.Label(tab4, textvariable=auto_analysis_path_var)
auto_analysis_file_label.pack()

label_var_auto_analysis = tk.StringVar()
label_var_auto_analysis.set("None")
tk.Label(tab4, text="Select Type").pack(pady=(20, 5))
label_frame = tk.Frame(tab4)
label_frame.pack()
for lbl in ["Healthy(GSDA)", "Patient(GSDB)"]:
    tk.Radiobutton(label_frame, text=lbl, variable=label_var_auto_analysis, value=lbl).pack(side="left", padx=20)

run_auto_analysis_button = tk.Button(tab4, text="Run Auto Analysis", command=run_auto_analysis)
run_auto_analysis_button.pack(pady=10)

progress_text = auto_analysis_progress(tab4, font_size=10)
progress_text.clear() 

# -------------------------Running the GUI---------------------------------
root.mainloop()