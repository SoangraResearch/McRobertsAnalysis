import os
import sys

# Add parent directory to sys.path so 'from Main.X' imports resolve when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

# OMX reader (Octave) and Tab 4 batch logic live outside this file.
from OMX_To_CSV import process_omx_file
from Main.GUI_Tabs.Tab4.auto_analysis_progress import auto_analysis_progress
from Main.GUI_Tabs.Tab4.Auto_analysis_code import (
    combine_segment_batch_results_to_tables,
    combine_tab2_per_chunk_export_tables,
    run_segment_batch_analysis,
    run_sequence_detection_per_chunk,
    select_segments_for_auto_analysis,
    split_data_by_day,
)

# Each tab’s behavior is in its controller; this module mostly wires widgets and callbacks.
from Main.GUI_Tabs.Tab1.Tab1Controller import Tab1Controller
from Main.GUI_Tabs.Tab2.Tab2Controller import Tab2Controller
from Main.GUI_Tabs.Tab3.Tab3Controller import Tab3Controller

# OMX paths and local imports (GSDA_code, etc.) assume the working directory is Main/.
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
tab_control.add(tab3, text="Analysis")

tab4 = tk.Frame(tab_control)
tab_control.add(tab4, text="Auto-Analysis (WIP)")

tab_control.pack(expand=1, fill='both')

# --- Shared / legacy GUI state (mostly Tab 1–3). Controllers also keep their own file paths. ---
plot_frame_OMX = None
acceleration_plot = None
mobiliseD_file = None
mobiliseD_directory_path = None
mobilised_path_var = tk.StringVar()
analysis_code_path_var = tk.StringVar()
linear_plots = None
nonlinear_plots = None
exported_csv_path = "None"
start_time_var = tk.StringVar()
stop_time_var = tk.StringVar()
file_start_time_var = tk.StringVar()
file_stop_time_var = tk.StringVar()
label_var = tk.StringVar()
export_format_var = tk.StringVar()

# --- Tab 4 only: OMX path, per-day GSD output, and flattened long-segment list for batch analysis. ---
auto_analysis_file = "None"
auto_analysis_per_chunk_results = None
auto_analysis_selected_segments = None
auto_analysis_batch_results = None  # per-segment Tab 3 linear + nonlinear outputs

# -------------------------Tab 1 Methods---------------------------------

def export_csv():
    tab1_controller.export_csv()
    # Point Mobilise-D Tab and Analysis Tab at the same exported CSV name/path.
    mobilised_path_var.set(f"File loaded: {tab1_controller.export_filename}")
    tab2_controller.set_file(os.path.join(tab1_controller.export_folder, tab1_controller.export_filename + ".csv"))
    analysis_code_path_var.set(f"File loaded: {tab1_controller.export_filename}")
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
tk.Button(gsd_frame, text="Run GSD Detection", command=lambda: tab2_controller.process_GSD(label_var_MobiliseD.get(), force_data_as_walking.get(), plot_left_GSD, plot_right_GSD, extra_plots=1)).pack(side="left", padx=10) #set extra plots to 1 to display plots

# Shared with Tab 4 auto analysis so GSD uses the same “force walking” flag as Mobilise-D.
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

def load_analysis_code_file():
    analysis_code_path_var.set(tab3_controller.load_file())

# -------------------------Tab 3 Analysis---------------------------------

tk.Button(tab3, text="Load CSV File", command=load_analysis_code_file).pack(pady=10)

analysis_code_path_var = tk.StringVar(value="File loaded: (none)")
analysis_file_label = tk.Label(tab3, textvariable=analysis_code_path_var)
analysis_file_label.pack()

analysis_frame = tk.Frame(tab3)
analysis_frame.pack(pady=5)

assume_walking_var = tk.BooleanVar(value=False)
plot_frame_analysis = tk.Frame(tab3, height=300)

tk.Button(analysis_frame, text="Linear Analysis", width=15, command=lambda: tab3_controller.do_linear_analysis(plot_frame_analysis, assume_walking_var)).pack(side="left", padx=10)
tk.Button(analysis_frame, text="Non-Linear Analysis", width=15, command=lambda: tab3_controller.do_nonlinear_analysis(plot_frame_analysis, assume_walking_var)).pack(side="left", padx=10)

tk.Checkbutton(analysis_frame, text="Assume data is walking", variable=assume_walking_var).pack(side="left", padx=10)

plot_frame_analysis.pack(fill="both", expand=True)

button_frame = tk.Frame(tab3)
button_frame.pack(pady=5)

tk.Button(button_frame, text="Save Linear Analysis", command=lambda: tab3_controller.save_linear_analysis(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save Non-Linear Analysis", command=lambda: tab3_controller.save_nonlinear_analysis(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save All Linear Analysis Plots", command=lambda: tab3_controller.save_all_linear_analysis_plots(True)).pack(side="left", padx=5)
tk.Button(button_frame, text="Save All Non-Linear Analysis Plots", command=lambda: tab3_controller.save_all_nonlinear_analysis_plots(True)).pack(side="left", padx=5)

tk.Button(tab3, text="Save All", command=lambda: tab3_controller.save_all_output()).pack(pady=5)

# -------------------------Tab 4 Methods (OMX → day chunks → GSD; no controller class yet) ---------------------------------
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
    global auto_analysis_file, auto_analysis_per_chunk_results, auto_analysis_selected_segments, auto_analysis_batch_results
    if (auto_analysis_file == "None"):
        messagebox.showerror("Error", "File not loaded")
        return

    if (label_var_auto_analysis.get() == "None"):
        messagebox.showerror("Error", "GSD algorithm not set")
        return
    
    progress_text.clear()

    try:
        # Drop any previous results so a failed run does not leave stale data.
        auto_analysis_per_chunk_results = None
        auto_analysis_selected_segments = None
        auto_analysis_batch_results = None
        progress_text.update_progress("Reading Data")

        auto_analysis_data, _filename = process_omx_file(auto_analysis_file)
        timestamps = auto_analysis_data['ACC'][:, 0]

        progress_text.update_progress("Splitting Data")

        data_chunks = split_data_by_day(auto_analysis_data, timestamps)

        progress_text.update_progress("Sequence Detection")

        # Healthy vs Patient chooses gsd_iluz vs gsd_low_back_acc inside Auto_analysis_code.
        auto_analysis_per_chunk_results = run_sequence_detection_per_chunk(
            data_chunks,
            label_var_auto_analysis.get(),
            # Tab 4 checkbox value (separate from Tab 2’s Mobilise-D checkbox).
            force_data_as_walking_tab4.get(),
        )

        progress_text.update_progress("Segment Selection")
        # One row per long bout: chunk_index + segment dict (Start/End relative to that chunk).
        auto_analysis_selected_segments = select_segments_for_auto_analysis(
            auto_analysis_per_chunk_results
        )

        progress_text.update_progress("Segment Analysis")
        # Temp CSV per bout; Tab 3 analysis on main thread (UI may pause for large batches).
        auto_analysis_batch_results = run_segment_batch_analysis(
            data_chunks,
            auto_analysis_selected_segments,
            assume_walking=True,
        )

        progress_text.update_progress("Output")

        n_sel = len(auto_analysis_selected_segments)
        n_ok = sum(1 for r in auto_analysis_batch_results if r.get("error") is None)
        n_fail = len(auto_analysis_batch_results) - n_ok

        # Consolidate all per-segment results into combined tables and let the user save them as CSVs.
        linear_all_df, nonlinear_all_df, failures = combine_segment_batch_results_to_tables(
            auto_analysis_batch_results
        )

        base_dir = os.path.dirname(auto_analysis_file)
        base_name = os.path.splitext(os.path.basename(auto_analysis_file))[0]

        saved_any = False
        saved_paths = []
        tab2_export_note = ""

        # Optional Tab 2–style export:
        # If the checkbox is enabled, we prompt the user to save CSVs that mirror
        # Tab 2 outputs (GSD gait sequences and step counts), but combined across
        # all day-chunks processed in this Tab 4 run.
        if save_tab2_auto_results.get():
            gsd_all_df, step_all_df = combine_tab2_per_chunk_export_tables(
                auto_analysis_per_chunk_results
            )
            # Save GSD results for all day chunks (stacked into one table).
            if not gsd_all_df.empty:
                default_gsd = f"{base_name}_tab4_GSD_results.csv"
                gsd_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv")],
                    initialdir=base_dir,
                    initialfile=default_gsd,
                    title="Save Tab 2–style GSD results (all day chunks)",
                )
                if gsd_path:
                    gsd_all_df.to_csv(gsd_path, index=False)
                    saved_any = True
                    saved_paths.append(os.path.basename(gsd_path))
            # Save step counts for all day chunks (stacked into one table).
            if not step_all_df.empty:
                default_steps = f"{base_name}_tab4_step_counts.csv"
                step_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv")],
                    initialdir=base_dir,
                    initialfile=default_steps,
                    title="Save Tab 2–style step counts (all day chunks)",
                )
                if step_path:
                    step_all_df.to_csv(step_path, index=False)
                    saved_any = True
                    saved_paths.append(os.path.basename(step_path))
            # If both tables are empty, show a short note in the final summary.
            if gsd_all_df.empty and step_all_df.empty:
                tab2_export_note = (
                    "Tab 2 export: no GSD/step rows (all day chunks empty or skipped).\n\n"
                )

        if not linear_all_df.empty:
            default_linear = f"{base_name}_tab4_linear_segments.csv"
            linear_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialdir=base_dir,
                initialfile=default_linear,
                title="Save Tab4 Linear Segments (CSV)",
            )
            if linear_path:
                linear_all_df.to_csv(linear_path, index=False)
                saved_any = True
                saved_paths.append(os.path.basename(linear_path))

        if not nonlinear_all_df.empty:
            default_nonlinear = f"{base_name}_tab4_nonlinear_segments.csv"
            nonlinear_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialdir=base_dir,
                initialfile=default_nonlinear,
                title="Save Tab4 Nonlinear Segments (CSV)",
            )
            if nonlinear_path:
                nonlinear_all_df.to_csv(nonlinear_path, index=False)
                saved_any = True
                saved_paths.append(os.path.basename(nonlinear_path))

        summary_msg = tab2_export_note + (
            f"Day chunks: {len(data_chunks)}\n"
            f"Long segments selected: {n_sel}\n"
            f"Analyzed OK: {n_ok}, failed: {n_fail}\n"
        )
        if saved_any:
            summary_msg += "Saved:\n" + "\n".join(saved_paths)
        else:
            if (linear_all_df.empty) and (nonlinear_all_df.empty):
                summary_msg += "\nNo successful segment outputs to save."
            else:
                summary_msg += "\nNo CSVs saved (prompts cancelled)."

        messagebox.showinfo("Auto Analysis", summary_msg)

    except Exception as e:
        auto_analysis_per_chunk_results = None
        auto_analysis_selected_segments = None
        auto_analysis_batch_results = None
        traceback.print_exc()
        messagebox.showerror("Auto Analysis Error", str(e))

# -------------------------Tab 4 Auto Analysis UI ---------------------------------
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

# Optional flag: forces the “walking” behavior inside the GSD/segment logic.
force_data_as_walking_tab4 = tk.BooleanVar(value=False)
tk.Checkbutton(tab4, text="Force Data as Walking", variable=force_data_as_walking_tab4).pack(pady=5)

# Offer save dialogs for Mobilise-D–style CSVs (Plots still require Tab 2.)
save_tab2_auto_results = tk.BooleanVar(value=False)
tk.Checkbutton(
    tab4,
    text="After run: offer to save Tab 2 results (GSD + step counts CSV)",
    variable=save_tab2_auto_results,
).pack(pady=2)

run_auto_analysis_button = tk.Button(tab4, text="Run Auto Analysis", command=run_auto_analysis)
run_auto_analysis_button.pack(pady=10)

progress_text = auto_analysis_progress(tab4, font_size=10)
progress_text.clear() 

# -------------------------Running the GUI---------------------------------
root.mainloop()