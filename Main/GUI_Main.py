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
from Main.GUI_Tabs.gui_style import (
    apply_notebook_tab_pointer_cursor,
    ensure_gui_style,
    make_action_button,
    make_checkbutton,
    make_radiobutton,
    restore_main_window_focus,
)
from Main.GUI_Tabs.heavy_job_runner import create_busy_status_strip
from Main.GUI_Tabs.Tab1.Tab1Controller import Tab1Controller
from Main.GUI_Tabs.Tab2.Tab2Controller import Tab2Controller
from Main import app_config
from Main.GUI_Tabs.Tab3.Tab3Controller import Tab3Controller
from Main.GUI_Tabs.Tab5.Tab5Controller import Tab5Controller

# OMX paths and local imports (GSDA_code, etc.) assume the working directory is Main/.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# -------------------------Tkinter Setup---------------------------------

# Create the main window
root = tk.Tk()
root.title("McRoberts Analysis")
root.geometry("1000x800")
ensure_gui_style(root)

_settings_warn = app_config.load_into_current()
if _settings_warn:
    messagebox.showwarning("Settings", _settings_warn, parent=root)

tab_control = ttk.Notebook(root)

tab1 = tk.Frame(tab_control)
tab_control.add(tab1, text="Select Data")

tab2 = tk.Frame(tab_control)
tab_control.add(tab2, text="Mobilise-D")

tab3 = tk.Frame(tab_control)
tab_control.add(tab3, text="Analysis")

tab4 = tk.Frame(tab_control)
tab_control.add(tab4, text="Auto-Analysis")

tab5 = tk.Frame(tab_control)
tab_control.add(tab5, text="Settings")

apply_notebook_tab_pointer_cursor(tab_control)

# Shared bottom status strip + worker runner (indeterminate/determinate progress).
heavy_job = create_busy_status_strip(root)

tab1_controller = Tab1Controller(tab1, heavy_job)
tab1_controller.build_octave_section()
tab2_controller = Tab2Controller(tab2, heavy_job)
tab3_controller = Tab3Controller(tab3, heavy_job)
tab5_controller = Tab5Controller(tab5)

tab_control.pack(expand=1, fill="both")

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
    def _after_tab1_csv_export():
        mobilised_path_var.set(f"File loaded: {tab1_controller.export_filename}")
        tab2_controller.set_file(
            os.path.join(
                tab1_controller.export_folder,
                tab1_controller.export_filename + ".csv",
            )
        )
        analysis_code_path_var.set(f"File loaded: {tab1_controller.export_filename}")
        tab3_controller.set_file(
            os.path.join(
                tab1_controller.export_folder,
                tab1_controller.export_filename + ".csv",
            )
        )

    tab1_controller.export_csv(after_export=_after_tab1_csv_export)
    
# -------------------------Tab 1 Select Data---------------------------------

# Plot frame first (referenced by load); no pack_propagate(False) so it can shrink
# with the window like Tab 2/3. Export row is packed to BOTTOM before the plot so
# it stays visible when the window is minimized or resized.
plot_frame_OMX = tk.Frame(tab1, height=300)

tab1_load_file_button = make_action_button(
    tab1, text="Load OMX File", command=lambda: tab1_controller.load_file(plot_frame_OMX)
)
tab1_load_file_button.pack(pady=10)

tab1_controller.create_time_labels()

button_frame = tk.Frame(tab1)
button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
tk.Frame(button_frame).pack(side=tk.LEFT, expand=True)
button_inner = tk.Frame(button_frame)
button_inner.pack(side=tk.LEFT)

tab1_export_csv_button = make_action_button(
    button_inner, text="Export To CSV", command=lambda: export_csv()
)
tab1_export_csv_button.pack(side="left", padx=5)

tab1_export_plot_button = make_action_button(
    button_inner,
    text="Export Plot",
    command=lambda: tab1_controller.export_acceleration_plot(),
)
tab1_export_plot_button.pack(side="left", padx=5)

tk.Frame(button_frame).pack(side=tk.LEFT, expand=True)

plot_frame_OMX.pack(fill="both", expand=True)

# -------------------------Tab 2 Methods---------------------------------

def load_mobiliseD_file():
    mobilised_path_var.set(tab2_controller.load_file())

# -------------------------Tab 2 Mobilise D---------------------------------

tab2_load_csv_button = make_action_button(
    tab2, text="Load CSV File", command=lambda: load_mobiliseD_file()
)
tab2_load_csv_button.pack(pady=10)

mobilised_path_var = tk.StringVar(value="File loaded: (none)")
MobiliseD_file_label = tk.Label(tab2, textvariable=mobilised_path_var)
MobiliseD_file_label.pack()

label_var_MobiliseD = tk.StringVar()
label_var_MobiliseD.set("None")
tk.Label(tab2, text="Select Type").pack(pady=(20, 5))
label_frame = tk.Frame(tab2)
label_frame.pack(pady=(0, 4))
tab2_gsd_algorithm_radios = []
for lbl in ["Healthy(GSDA)", "Patient(GSDB)"]:
    rb = make_radiobutton(label_frame, text=lbl, variable=label_var_MobiliseD, value=lbl)
    rb.pack(side="left", padx=(16, 16), pady=8, ipadx=4, ipady=4)
    tab2_gsd_algorithm_radios.append(rb)

# container frame for button + checkbox
gsd_frame = tk.Frame(tab2)
gsd_frame.pack(pady=15)

tab2_run_gsd_button = make_action_button(
    gsd_frame,
    text="Run GSD Detection",
    command=lambda: tab2_controller.process_GSD(
        label_var_MobiliseD.get(),
        force_data_as_walking.get(),
        plot_left_GSD,
        plot_right_GSD,
        extra_plots=1,
    ),
)
tab2_run_gsd_button.pack(side="left", padx=10)  # extra_plots=1 to display plots

# Shared with Tab 4 auto analysis so GSD uses the same “force walking” flag as Mobilise-D.
force_data_as_walking = tk.BooleanVar(value=False)
tab2_force_walking_check = make_checkbutton(
    gsd_frame, text="Force Data as Walking", variable=force_data_as_walking
)
tab2_force_walking_check.pack(side="left", padx=(14, 10), pady=4, ipadx=4, ipady=4)

plot_frame_GSD = tk.Frame(tab2, height=300)
plot_frame_GSD.pack(fill="both", expand=True)

# Left and right frames inside plot_frame_GSD
plot_left_GSD = tk.Frame(plot_frame_GSD, width=500)
plot_left_GSD.pack(side='left', fill='both', expand=True)

plot_right_GSD = tk.Frame(plot_frame_GSD, width=500)
plot_right_GSD.pack(side='left', fill='both', expand=True)

# Create a frame to hold the buttons horizontally
tab2_save_button_frame = tk.Frame(tab2)
tab2_save_button_frame.pack(pady=5)

tab2_save_gsd_result_button = make_action_button(
    tab2_save_button_frame,
    text="Save GSD Result",
    command=lambda: tab2_controller.save_GSD_results(True),
)
tab2_save_gsd_result_button.pack(side="left", padx=5)
tab2_save_gsd_plot_button = make_action_button(
    tab2_save_button_frame,
    text="Save GSD plot",
    command=lambda: tab2_controller.save_GSD_plot(True),
)
tab2_save_gsd_plot_button.pack(side="left", padx=5)
tab2_save_step_counts_button = make_action_button(
    tab2_save_button_frame,
    text="Save Step Counts",
    command=lambda: tab2_controller.save_step_counts(True),
)
tab2_save_step_counts_button.pack(side="left", padx=5)
tab2_save_steps_plot_button = make_action_button(
    tab2_save_button_frame,
    text="Save Steps plot",
    command=lambda: tab2_controller.save_steps_plot(True),
)
tab2_save_steps_plot_button.pack(side="left", padx=5)

tab2_save_all_button = make_action_button(
    tab2, text="Save All", command=lambda: tab2_controller.save_all_GSD()
)
tab2_save_all_button.pack(pady=5)

# -------------------------Tab 3 Methods---------------------------------

def load_analysis_code_file():
    analysis_code_path_var.set(tab3_controller.load_file())

# -------------------------Tab 3 Analysis---------------------------------

tab3_load_csv_button = make_action_button(
    tab3, text="Load CSV File", command=load_analysis_code_file
)
tab3_load_csv_button.pack(pady=10)

analysis_code_path_var = tk.StringVar(value="File loaded: (none)")
analysis_file_label = tk.Label(tab3, textvariable=analysis_code_path_var)
analysis_file_label.pack()

analysis_frame = tk.Frame(tab3)
analysis_frame.pack(pady=5)

assume_walking_var = tk.BooleanVar(value=False)
plot_frame_analysis = tk.Frame(tab3, height=300)

tab3_linear_button = make_action_button(
    analysis_frame,
    text="Linear Analysis",
    width=15,
    command=lambda: tab3_controller.do_linear_analysis(
        plot_frame_analysis, assume_walking_var
    ),
)
tab3_linear_button.pack(side="left", padx=10)
tab3_nonlinear_button = make_action_button(
    analysis_frame,
    text="Non-Linear Analysis",
    width=15,
    command=lambda: tab3_controller.do_nonlinear_analysis(
        plot_frame_analysis, assume_walking_var
    ),
)
tab3_nonlinear_button.pack(side="left", padx=10)

tab3_assume_walking_check = make_checkbutton(
    analysis_frame, text="Assume data is walking", variable=assume_walking_var
)
tab3_assume_walking_check.pack(side="left", padx=(12, 12), pady=6, ipadx=4, ipady=4)

plot_frame_analysis.pack(fill="both", expand=True)

tab3_save_button_frame = tk.Frame(tab3)
tab3_save_button_frame.pack(pady=5)

tab3_save_linear_csv_button = make_action_button(
    tab3_save_button_frame,
    text="Save Linear Analysis",
    command=lambda: tab3_controller.save_linear_analysis(True),
)
tab3_save_linear_csv_button.pack(side="left", padx=5)
tab3_save_nonlinear_csv_button = make_action_button(
    tab3_save_button_frame,
    text="Save Non-Linear Analysis",
    command=lambda: tab3_controller.save_nonlinear_analysis(True),
)
tab3_save_nonlinear_csv_button.pack(side="left", padx=5)
tab3_save_all_linear_plots_button = make_action_button(
    tab3_save_button_frame,
    text="Save All Linear Analysis Plots",
    command=lambda: tab3_controller.save_all_linear_analysis_plots(True),
)
tab3_save_all_linear_plots_button.pack(side="left", padx=5)
tab3_save_all_nonlinear_plots_button = make_action_button(
    tab3_save_button_frame,
    text="Save All Non-Linear Analysis Plots",
    command=lambda: tab3_controller.save_all_nonlinear_analysis_plots(True),
)
tab3_save_all_nonlinear_plots_button.pack(side="left", padx=5)

tab3_save_all_output_button = make_action_button(
    tab3, text="Save All", command=lambda: tab3_controller.save_all_output()
)
tab3_save_all_output_button.pack(pady=5)

# -------------------------Tab 4 Methods (OMX → day chunks → GSD; no controller class yet) ---------------------------------
def _tab4_resolve_output_folder_path(chosen_path):
    """Save-As path → folder path for CSV bundle (same dialog style as other tabs).

    If the user picks a name ending in .csv/.txt, treat it as a folder name and strip
    the extension so we create a directory, not overwrite a CSV by mistake.
    """
    if not chosen_path:
        return None
    p = chosen_path.strip()
    if p.lower().endswith((".csv", ".txt")):
        return os.path.splitext(p)[0]
    return p


def load_auto_analysis_file():
    global auto_analysis_file
    file_path = filedialog.askopenfilename(filetypes=[("OMX file", "*.OMX")])
    restore_main_window_focus(root)
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
    if auto_analysis_file == "None":
        messagebox.showerror("Error", "File not loaded")
        return

    if label_var_auto_analysis.get() == "None":
        messagebox.showerror("Error", "GSD algorithm not set")
        return

    file_path = auto_analysis_file
    gsd_type = label_var_auto_analysis.get()
    force_walk = force_data_as_walking_tab4.get()
    save_tab2 = save_tab2_auto_results.get()

    progress_text.clear()

    def sync_tab4_canvas(step_name: str) -> None:
        def apply() -> None:
            progress_text.update_progress(step_name)

        heavy_job.schedule_main(apply)

    def notify_status(msg: str) -> None:
        heavy_job.schedule_status_message(f"Auto analysis: {msg}")

    def worker():
        sync_tab4_canvas("Reading Data")
        notify_status("Reading OMX file…")
        auto_analysis_data, _filename = process_omx_file(file_path)
        timestamps = auto_analysis_data["ACC"][:, 0]

        sync_tab4_canvas("Splitting Data")
        notify_status("Splitting data by day…")
        data_chunks = split_data_by_day(auto_analysis_data, timestamps)

        sync_tab4_canvas("Sequence Detection")
        notify_status("Sequence detection (GSD per day chunk)…")
        per_chunk = run_sequence_detection_per_chunk(
            data_chunks,
            gsd_type,
            force_walk,
        )

        sync_tab4_canvas("Segment Selection")
        notify_status("Selecting long segments…")
        selected = select_segments_for_auto_analysis(per_chunk)

        sync_tab4_canvas("Segment Analysis")
        batch_results = run_segment_batch_analysis(
            data_chunks,
            selected,
            assume_walking=True,
            progress_callback=notify_status,
        )

        sync_tab4_canvas("Output")
        notify_status("Combining results…")
        n_sel = len(selected)
        n_ok = sum(1 for r in batch_results if r.get("error") is None)
        n_fail = len(batch_results) - n_ok
        linear_all_df, nonlinear_all_df, _failures = (
            combine_segment_batch_results_to_tables(batch_results)
        )

        if save_tab2:
            gsd_all_df, step_all_df = combine_tab2_per_chunk_export_tables(per_chunk)
            tab2_empty = gsd_all_df.empty and step_all_df.empty
        else:
            gsd_all_df, step_all_df = None, None
            tab2_empty = False

        return {
            "per_chunk": per_chunk,
            "selected": selected,
            "batch_results": batch_results,
            "n_chunks": len(data_chunks),
            "n_sel": n_sel,
            "n_ok": n_ok,
            "n_fail": n_fail,
            "linear_all_df": linear_all_df,
            "nonlinear_all_df": nonlinear_all_df,
            "base_dir": os.path.dirname(file_path),
            "base_name": os.path.splitext(os.path.basename(file_path))[0],
            "save_tab2": save_tab2,
            "gsd_all_df": gsd_all_df,
            "step_all_df": step_all_df,
            "tab2_empty": tab2_empty,
        }

    def on_success(payload):
        global auto_analysis_per_chunk_results, auto_analysis_selected_segments, auto_analysis_batch_results
        auto_analysis_per_chunk_results = payload["per_chunk"]
        auto_analysis_selected_segments = payload["selected"]
        auto_analysis_batch_results = payload["batch_results"]

        linear_all_df = payload["linear_all_df"]
        nonlinear_all_df = payload["nonlinear_all_df"]
        n_sel = payload["n_sel"]
        n_ok = payload["n_ok"]
        n_fail = payload["n_fail"]
        data_chunks_len = payload["n_chunks"]
        base_dir = payload["base_dir"]
        base_name = payload["base_name"]
        save_tab2 = payload["save_tab2"]
        gsd_all_df = payload["gsd_all_df"]
        step_all_df = payload["step_all_df"]

        tab2_export_note = ""
        if save_tab2 and payload["tab2_empty"]:
            tab2_export_note = (
                "Tab 2 export: no GSD/step rows (all day chunks empty or skipped).\n\n"
            )

        want_tab2_gsd = (
            save_tab2 and gsd_all_df is not None and not gsd_all_df.empty
        )
        want_tab2_steps = (
            save_tab2 and step_all_df is not None and not step_all_df.empty
        )
        want_linear = not linear_all_df.empty
        want_nonlinear = not nonlinear_all_df.empty
        anything_to_save = (
            want_tab2_gsd or want_tab2_steps or want_linear or want_nonlinear
        )

        saved_any = False
        saved_paths = []
        output_dir = None
        if anything_to_save:
            chosen = filedialog.asksaveasfilename(
                initialdir=base_dir,
                initialfile=f"{base_name}_AutoAnalysis",
                title="Save Auto-Analysis output folder",
                defaultextension="",
                filetypes=[("All files", "*.*")],
            )
            restore_main_window_focus(root)
            output_dir = _tab4_resolve_output_folder_path(chosen)
            if output_dir:
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    if want_tab2_gsd:
                        p = os.path.join(
                            output_dir, f"{base_name}_tab4_GSD_results.csv"
                        )
                        gsd_all_df.to_csv(p, index=False)
                        saved_any = True
                        saved_paths.append(p)
                    if want_tab2_steps:
                        p = os.path.join(
                            output_dir, f"{base_name}_tab4_step_counts.csv"
                        )
                        step_all_df.to_csv(p, index=False)
                        saved_any = True
                        saved_paths.append(p)
                    if want_linear:
                        p = os.path.join(
                            output_dir, f"{base_name}_tab4_linear_segments.csv"
                        )
                        linear_all_df.to_csv(p, index=False)
                        saved_any = True
                        saved_paths.append(p)
                    if want_nonlinear:
                        p = os.path.join(
                            output_dir, f"{base_name}_tab4_nonlinear_segments.csv"
                        )
                        nonlinear_all_df.to_csv(p, index=False)
                        saved_any = True
                        saved_paths.append(p)
                except OSError as e:
                    messagebox.showerror("Save Error", str(e))

        summary_msg = tab2_export_note + (
            f"Day chunks: {data_chunks_len}\n"
            f"Long segments selected: {n_sel}\n"
            f"Analyzed OK: {n_ok}, failed: {n_fail}\n"
        )
        if saved_any:
            summary_msg += "Saved to folder:\n" + output_dir + "\n\nFiles:\n" + "\n".join(
                os.path.basename(p) for p in saved_paths
            )
        else:
            if not anything_to_save:
                summary_msg += "\nNo CSV outputs to write (all tables empty)."
            elif not output_dir:
                summary_msg += "\nNo CSVs saved (output location cancelled)."
            else:
                summary_msg += "\nNo CSVs saved."

        messagebox.showinfo("Auto Analysis", summary_msg)
        progress_text.clear()

    def on_error(msg: str):
        global auto_analysis_per_chunk_results, auto_analysis_selected_segments, auto_analysis_batch_results
        auto_analysis_per_chunk_results = None
        auto_analysis_selected_segments = None
        auto_analysis_batch_results = None
        progress_text.clear()
        messagebox.showerror("Auto Analysis Error", msg)

    if not heavy_job.run(
        "Auto analysis…",
        worker,
        on_success=on_success,
        on_error=on_error,
    ):
        return

# -------------------------Tab 4 Auto Analysis UI ---------------------------------
tab4_load_omx_button = make_action_button(
    tab4, text="Load OMX File", command=load_auto_analysis_file
)
tab4_load_omx_button.pack(pady=10)

auto_analysis_path_var = tk.StringVar(value="File loaded: (none)")
auto_analysis_file_label = tk.Label(tab4, textvariable=auto_analysis_path_var)
auto_analysis_file_label.pack()

label_var_auto_analysis = tk.StringVar()
label_var_auto_analysis.set("None")
tk.Label(tab4, text="Select Type").pack(pady=(20, 5))
label_frame = tk.Frame(tab4)
label_frame.pack(pady=(0, 4))
tab4_gsd_algorithm_radios = []
for lbl in ["Healthy(GSDA)", "Patient(GSDB)"]:
    rb = make_radiobutton(label_frame, text=lbl, variable=label_var_auto_analysis, value=lbl)
    rb.pack(side="left", padx=(16, 16), pady=8, ipadx=4, ipady=4)
    tab4_gsd_algorithm_radios.append(rb)

# Optional flag: forces the “walking” behavior inside the GSD/segment logic.
force_data_as_walking_tab4 = tk.BooleanVar(value=False)
tab4_force_walking_check = make_checkbutton(
    tab4, text="Force Data as Walking", variable=force_data_as_walking_tab4
)
tab4_force_walking_check.pack(pady=(10, 6), ipadx=4, ipady=4)

# Include Tab 2–style GSD + step CSVs in the same output folder (no Tab 2 plots).
save_tab2_auto_results = tk.BooleanVar(value=False)
tab4_save_tab2_results_check = make_checkbutton(
    tab4,
    text="Save Tab 2 results (GSD + step counts CSV)",
    variable=save_tab2_auto_results,
)
tab4_save_tab2_results_check.pack(pady=(4, 6), ipadx=4, ipady=4)

run_auto_analysis_button = make_action_button(tab4, text="Run Auto Analysis", command=run_auto_analysis)
run_auto_analysis_button.pack(pady=10)

progress_text = auto_analysis_progress(tab4, font_size=10)
progress_text.clear()

heavy_job.register_disable_widgets(
    tab_control,
    tab1_load_file_button,
    tab1_export_csv_button,
    tab1_export_plot_button,
    tab2_load_csv_button,
    tab2_run_gsd_button,
    tab2_force_walking_check,
    tab2_save_gsd_result_button,
    tab2_save_gsd_plot_button,
    tab2_save_step_counts_button,
    tab2_save_steps_plot_button,
    tab2_save_all_button,
    tab3_load_csv_button,
    tab3_linear_button,
    tab3_nonlinear_button,
    tab3_assume_walking_check,
    tab3_save_linear_csv_button,
    tab3_save_nonlinear_csv_button,
    tab3_save_all_linear_plots_button,
    tab3_save_all_nonlinear_plots_button,
    tab3_save_all_output_button,
    tab4_load_omx_button,
    tab4_force_walking_check,
    tab4_save_tab2_results_check,
    run_auto_analysis_button,
    *tab2_gsd_algorithm_radios,
    *tab4_gsd_algorithm_radios,
)

# -------------------------Running the GUI---------------------------------
root.mainloop()