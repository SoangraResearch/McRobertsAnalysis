import os
import csv
import tkinter as tk
import pandas as pd
import numpy as np
from datetime import timedelta, datetime
from tkinter import filedialog, messagebox, ttk
import matplotlib.dates as mdates
from ICDA_code import step_detection
from OMX_To_CSV import process_omx_file, matlab_datenum_to_datetime
from Acceleration_Plot import PlotOMX
from GSD_plots import plot_GSDA, plot_GSDB, plot_steps
from Ayush_Analysis import linear_analysis, nonlinear_analysis
from Ayush_Analysis_Plot import display_combined_plots

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
tab3 = tk.Frame(tab_control)
tab_control.add(tab1, text="Select Data")
tab_control.add(tab2, text="Mobilise-D")
tab_control.add(tab3, text="Ayush's Code")

tab_control.pack(expand=1, fill='both')

plot_frame_OMX = None
acceleration_plot = None
mobiliseD_file = None
mobiliseD_directory_path = None
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

def create_tab1_export_folder():
    global new_filename, export_folder
    safe_start = start_time_var.get().replace(":", "-").replace(" ", "_")
    safe_stop = stop_time_var.get().replace(":", "-").replace(" ", "_")

    new_filename = filename + "_from_" + safe_start + "_to_" + safe_stop

    export_folder = os.path.join(os.getcwd(), "../Data/Output/" + filename + "/" + new_filename)
    os.makedirs(export_folder, exist_ok=True)

def export_csv():
    global mobiliseD_file, new_filename, export_folder, mobiliseD_directory_path, mobiliseD_filename, ayush_code_file, ayush_code_directory_path, ayush_code_filename
    create_tab1_export_folder()

    output_path=filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        initialdir=export_folder,
        initialfile=new_filename,
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
    ayush_code_file = output_path
    mobiliseD_filename = new_filename
    ayush_code_filename = new_filename
    mobiliseD_directory_path = export_folder
    ayush_code_directory_path = export_folder
    mobilised_path_var.set(f"File loaded: {new_filename}")
    ayush_code_path_var.set(f"File loaded: {new_filename}")

def export_acceleration_plot():
    create_tab1_export_folder()

    output_path=filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf"), ("SVG File", "*.svg")],
        initialdir=export_folder,
        initialfile=new_filename + "_acceleration_plot",
        title="Save Acceleration Plot"
    )

    if output_path:
        try:
            acceleration_plot.fig.savefig(output_path, dpi=300)
            messagebox.showinfo("Success", f"File saved to:\n{output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")
        
# -------------------------Tab 2 Methods---------------------------------
def load_mobiliseD_file():
    global mobiliseD_file, mobiliseD_directory_path, mobiliseD_filename
    file_path = filedialog.askopenfilename(filetypes=[("CSV/JSON files", "*.csv *.json")])
    if not file_path:
        return
    mobiliseD_directory_path = os.path.dirname(file_path)
    mobiliseD_filename = os.path.splitext(os.path.basename(file_path))[0]
    try:
        if file_path.endswith(".csv"):
            messagebox.showinfo("Loaded", f"Loaded file:\n{file_path}")
            mobiliseD_file = file_path
            mobilised_path_var.set(f"File loaded: {mobiliseD_filename}")
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
    global mobiliseD_df, gsd_result, sd_result_df, gsd_plot, step_result_df, steps_plot
    convert_mobiliseD_file_to_df()

    try:
        acc = mobiliseD_df.iloc[:, 1:4].to_numpy()
        time_col = mobiliseD_df['Time'].to_numpy()
        original_time_array = [matlab_datenum_to_datetime(t) for t in time_col]
        fs = 100
        print(label_var_MobiliseD.get())
        if label_var_MobiliseD.get() == "Healthy(GSDA)":
            from GSDA_code import gsd_iluz
            imu_input = {"LowerBack": {"Acc": acc, "Gyr": np.zeros_like(acc), "Fs": {"Acc": fs}}}
            gsd_result, gait_bool_for_plot, v_acc_for_plot = gsd_iluz(imu_input, time_vector=original_time_array, plot_results=False)
            gsd_plot = plot_GSDA(gait_bool_for_plot, v_acc_for_plot, plot_left_GSD)
        elif label_var_MobiliseD.get() == "Patient(GSDB)":
            from GSDB_code import gsd_low_back_acc
            gsd_result, sig_det_act_for_plot, walk_label_for_plot = gsd_low_back_acc(acc, fs, plot_results=False, time_vector=original_time_array)
            gsd_plot = plot_GSDB(sig_det_act_for_plot, walk_label_for_plot, plot_left_GSD)
        else:
            gsd_result = -1
        sd_result_df = pd.DataFrame(gsd_result)
        step_result = step_detection(acc, gsd_result, fs, plot_results=False)
        step_result_df = pd.DataFrame(gsd_result)
        steps_plot = plot_steps(gsd_result, fs, v_acc_for_plot, plot_right_GSD)
        messagebox.showinfo("GSD Result", f"Gait sequences found: {len(gsd_result)}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def create_tab2_export_folder():
    global export_folder, mobiliseD_directory_path

    export_folder = mobiliseD_directory_path
    os.makedirs(export_folder, exist_ok=True)
    
def save_GSD_results(open_prompt_window):
    create_tab2_export_folder()

    try:
        if sd_result_df is None:
            messagebox.showerror("Error", "No GSD result to save.")
            return
        if open_prompt_window:
            output_path=filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialdir=export_folder,
                initialfile=mobiliseD_filename + "_GSD_results",
                title="Save GSD results"
            )
            if not output_path:
                return False
        else:
            output_path = os.path.join(export_folder, mobiliseD_filename + "_GSD_results.csv")
        sd_result_df.to_csv(output_path, index=False)
        messagebox.showinfo("Saved", f"GSD result saved to: {output_path}")
    except Exception as e:
        messagebox.showerror("Save Error", str(e))

def save_GSD_plot(open_prompt_window):
    create_tab2_export_folder()
    try:
        if gsd_plot is None:
            messagebox.showerror("Error", "No GSD plot to save.")
            return
        if open_prompt_window:
            output_path=filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf"), ("SVG File", "*.svg")],
                initialdir=export_folder,
                initialfile=mobiliseD_filename + "_GSD_plot",
                title="Save GSD plot"
            )
            if not output_path:
                return False
        else:
            output_path = os.path.join(export_folder, mobiliseD_filename + "_GSD_plot.png")
        gsd_plot.savefig(output_path, dpi=300)
        messagebox.showinfo("Saved", f"GSD plot saved to: {output_path}")
    except Exception as e:
        messagebox.showerror("Save Error", str(e))

def save_step_counts(open_prompt_window):
    create_tab2_export_folder()

    try:
        if step_result_df is None:
            messagebox.showerror("Error", "No step counts to save.")
            return
        if open_prompt_window:
            output_path=filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialdir=export_folder,
                initialfile=mobiliseD_filename + "_step_counts",
                title="Save step counts"
            )
            if not output_path:
                return False
        else:
            output_path = os.path.join(export_folder, mobiliseD_filename + "_step_counts.csv")
        step_result_df.to_csv(output_path, index=False)
        messagebox.showinfo("Saved", f"step counts saved to: {output_path}")
    except Exception as e:
        messagebox.showerror("Save Error", str(e))

def save_steps_plot(open_prompt_window):
    create_tab2_export_folder()
    try:
        if steps_plot is None:
            messagebox.showerror("Error", "No steps plot to save.")
            return
        if open_prompt_window:
            output_path=filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf"), ("SVG File", "*.svg")],
                initialdir=export_folder,
                initialfile=mobiliseD_filename + "_steps_plot",
                title="Save steps plot"
            )
            if not output_path:
                return False
        else:
            output_path = os.path.join(export_folder, mobiliseD_filename + "_steps_plot.png")
        steps_plot.savefig(output_path, dpi=300)
        messagebox.showinfo("Saved", f"steps plot saved to: {output_path}")
    except Exception as e:
        messagebox.showerror("Save Error", str(e))

def save_all_GSD():
    try:
        save_GSD_results(False)
        save_GSD_plot(False)
        save_step_counts(False)
        save_steps_plot(False)
    except Exception as e:
        messagebox.showerror("Save Error", str(e))

# -------------------------Tab 3 Methods---------------------------------
def load_ayush_code_file():
    global ayush_code_directory_path, ayush_code_filename, ayush_code_file
    file_path = filedialog.askopenfilename(filetypes=[("CSV/JSON files", "*.csv *.json")])
    if not file_path:
        return
    ayush_code_directory_path = os.path.dirname(file_path)
    ayush_code_filename = os.path.splitext(os.path.basename(file_path))[0]

    try:
        if file_path.endswith(".csv"):
            messagebox.showinfo("Loaded", f"Loaded file:\n{file_path}")
            ayush_code_file = file_path
            ayush_code_path_var.set(f"File loaded: {ayush_code_filename}")
        else:
            raise ValueError("Unsupported file format")
    except Exception as e:
        messagebox.showerror("Load Error", str(e))

def ayush_analyze_data():
    global linear_df, nonlinear_df, linear_plots, nonlinear_plots
    linear_df, linear_plots = linear_analysis(ayush_code_file, plot_frame_ayush_code)
    nonlinear_df, nonlinear_plots = nonlinear_analysis(ayush_code_file, plot_frame_ayush_code)
    display_combined_plots(linear_plots, nonlinear_plots, plot_frame_ayush_code)

def create_tab3_export_folder():
    global export_folder, ayush_code_directory_path

    export_folder = ayush_code_directory_path
    os.makedirs(export_folder, exist_ok=True)

def save_linear_analysis(open_prompt_window):
    create_tab3_export_folder()
    try:
        if linear_df is None:
            messagebox.showerror("Error", "No linear analysis to save.")
            return
        if open_prompt_window:
            output_path=filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialdir=export_folder,
                initialfile=ayush_code_filename + "_linear_analysis",
                title="Save linear analysis"
            )
            if not output_path:
                return False
        else:
            output_path = os.path.join(export_folder, ayush_code_filename + "_linear_analysis.csv")
            linear_df.to_csv(output_path, index=False)
            messagebox.showinfo("Saved", f"linear analysis saved to: {output_path}")
    except Exception as e:
        messagebox.showerror("Save Error", str(e))

def save_nonlinear_analysis(open_prompt_window):
    create_tab3_export_folder()
    try:
        if nonlinear_df is None:
            messagebox.showerror("Error", "No nonlinear analysis to save.")
            return
        if open_prompt_window:
            output_path=filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialdir=export_folder,
                initialfile=ayush_code_filename + "_nonlinear_analysis",
                title="Save nonlinear analysis"
            )
            if not output_path:
                return False
        else:
            output_path = os.path.join(export_folder, ayush_code_filename + "_nonlinear_analysis.csv")
            nonlinear_df.to_csv(output_path, index=False)
            messagebox.showinfo("Saved", f"nonlinear analysis saved to: {output_path}")
    except Exception as e:
        messagebox.showerror("Save Error", str(e))

def save_linear_analysis_plot(open_prompt_window):
    create_tab3_export_folder()
    try:
        #TODO: replace with linear analysis plot
        if steps_plot is None:
            messagebox.showerror("Error", "No linear analysis plot to save.")
            return
        if open_prompt_window:
            output_path=filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf"), ("SVG File", "*.svg")],
                initialdir=export_folder,
                initialfile=ayush_code_filename + "_linear_analysis",
                title="Save linear analysis plot"
            )
            if not output_path:
                return False
        else:
            output_path = os.path.join(export_folder, ayush_code_filename + "_linear_analysis.png")
        steps_plot.savefig(output_path, dpi=300)
        messagebox.showinfo("Saved", f"linear analysis plot saved to: {output_path}")
    except Exception as e:
        messagebox.showerror("Save Error", str(e))

def save_all_ayush_code():
    try:
        save_linear_analysis(False)
        save_nonlinear_analysis(False)
        save_linear_analysis_plot(False)
    except Exception as e:
        messagebox.showerror("Save Error", str(e))
              
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
Export_Button.pack(side="left", padx=5)

Export_Button = tk.Button(button_frame, text="Export Plot", command=export_acceleration_plot)
Export_Button.pack(side="left", padx=5)

# -------------------------Tab 2 Mobilise D---------------------------------

tk.Button(tab2, text="Load CSV File", command=load_mobiliseD_file).pack(pady=10)

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
tk.Button(button_frame, text="Save GSD Result", command=lambda: save_GSD_results(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save GSD plot", command=lambda: save_GSD_plot(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save Step Counts", command=lambda: save_step_counts(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save Steps plot", command=lambda: save_steps_plot(True)).pack(side="left", padx=5)

tk.Button(tab2, text="Save All", command=save_all_GSD).pack(pady=5)

# -------------------------Tab 3 Ayush's Code---------------------------------

tk.Button(tab3, text="Load CSV File", command=load_ayush_code_file).pack(pady=10)

ayush_code_path_var = tk.StringVar(value="File loaded: (none)")
ayush_code_file_label = tk.Label(tab3, textvariable=ayush_code_path_var)
ayush_code_file_label.pack()

tk.Button(tab3, text="Analyze Data", command=ayush_analyze_data).pack(pady=20)

plot_frame_ayush_code = tk.Frame(tab3, height=300)
plot_frame_ayush_code.pack(fill="both", expand=True)

# Create a frame to hold the buttons horizontally
button_frame = tk.Frame(tab3)
button_frame.pack(pady=5)

# Add buttons side by side
tk.Button(button_frame, text="Save Linear Analysis", command=lambda: save_linear_analysis(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save Non-Lineal Analysis", command=lambda: save_nonlinear_analysis(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save Linear Analysis Plot", command=lambda: save_linear_analysis_plot(True)).pack(side="left", padx=5)

tk.Button(tab3, text="Save All", command=save_all_ayush_code).pack(pady=5)

# -------------------------Running the GUI---------------------------------
root.mainloop()