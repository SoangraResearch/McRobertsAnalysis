import os
import sys

# Add parent directory to sys.path so 'from Main.X' imports resolve when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

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
from Main.GUI_Tabs.Tab4.Tab4Controller import Tab4Controller
from Main.GUI_Tabs.Tab5.Tab5Controller import Tab5Controller
from Main.GUI_Tabs.Tab6.Tab6Controller import Tab6Controller

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
tab_control.add(tab3, text="Gait Analysis")

tab4 = tk.Frame(tab_control)
tab_control.add(tab4, text="Stance Analysis")

tab5 = tk.Frame(tab_control)
tab_control.add(tab5, text="Auto-Analysis")

tab6 = tk.Frame(tab_control)
tab_control.add(tab6, text="Settings")

apply_notebook_tab_pointer_cursor(tab_control)

# Shared bottom status strip + worker runner (indeterminate/determinate progress).
heavy_job = create_busy_status_strip(root)

tab1_controller = Tab1Controller(tab1, heavy_job)
tab1_controller.build_octave_section()
tab2_controller = Tab2Controller(tab2, heavy_job)
tab3_controller = Tab3Controller(tab3, heavy_job)
tab4_controller = Tab4Controller(tab4, heavy_job)
tab5_controller = Tab5Controller(tab5, heavy_job)
tab6_controller = Tab6Controller(tab6)

tab_control.pack(expand=1, fill="both")

# --- Shared / legacy GUI state (mostly Tab 1–3). Controllers also keep their own file paths. ---
plot_frame_OMX = None
acceleration_plot = None
mobiliseD_file = None
mobiliseD_directory_path = None
mobilised_path_var = tk.StringVar()
gait_analysis_code_path_var = tk.StringVar()
linear_plots = None
nonlinear_plots = None
exported_csv_path = "None"
start_time_var = tk.StringVar()
stop_time_var = tk.StringVar()
file_start_time_var = tk.StringVar()
file_stop_time_var = tk.StringVar()
label_var = tk.StringVar()
export_format_var = tk.StringVar()

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
        gait_analysis_code_path_var.set(f"File loaded: {tab1_controller.export_filename}")
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
        extra_plots=0,
    ),
)
# Hilbert pyplot windows must stay off here: GSD runs on a worker thread (macOS requires GUI on main).
tab2_run_gsd_button.pack(side="left", padx=10)

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
    gait_analysis_code_path_var.set(tab3_controller.load_file())

# -------------------------Tab 3 Gait Analysis---------------------------------

tab3_load_csv_button = make_action_button(
    tab3, text="Load CSV File", command=load_analysis_code_file
)
tab3_load_csv_button.pack(pady=10)

gait_analysis_code_path_var = tk.StringVar(value="File loaded: (none)")
gait_analysis_file_label = tk.Label(tab3, textvariable=gait_analysis_code_path_var)
gait_analysis_file_label.pack()

gait_analysis_frame = tk.Frame(tab3)
gait_analysis_frame.pack(pady=5)

gait_assume_walking_var = tk.BooleanVar(value=False)
plot_frame_gait_analysis = tk.Frame(tab3, height=300)

tab3_linear_button = make_action_button(
    gait_analysis_frame,
    text="Linear Analysis",
    width=15,
    command=lambda: tab3_controller.do_linear_analysis(
        plot_frame_gait_analysis, gait_assume_walking_var
    ),
)
tab3_linear_button.pack(side="left", padx=10)
tab3_nonlinear_button = make_action_button(
    gait_analysis_frame,
    text="Non-Linear Analysis",
    width=15,
    command=lambda: tab3_controller.do_nonlinear_analysis(
        plot_frame_gait_analysis, gait_assume_walking_var
    ),
)
tab3_nonlinear_button.pack(side="left", padx=10)

tab3_assume_walking_check = make_checkbutton(
    gait_analysis_frame, text="Assume data is walking", variable=gait_assume_walking_var
)
tab3_assume_walking_check.pack(side="left", padx=(12, 12), pady=6, ipadx=4, ipady=4)

plot_frame_gait_analysis.pack(fill="both", expand=True)

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

# -------------------------Tab 4 Methods---------------------------------

# -------------------------Tab 4 Stance Analysis---------------------------------

tab4_load_csv_button = make_action_button(
    tab4, text="Load CSV File"
)
tab4_load_csv_button.pack(pady=10)

stance_analysis_code_path_var = tk.StringVar(value="File loaded: (none)")
stance_analysis_file_label = tk.Label(tab4, textvariable=stance_analysis_code_path_var)
stance_analysis_file_label.pack()

stance_analysis_frame = tk.Frame(tab4)
stance_analysis_frame.pack(pady=5)

stance_assume_walking_var = tk.BooleanVar(value=False)
plot_frame_stance_analysis = tk.Frame(tab4, height=300)

tab4_analysis_button = make_action_button(
    stance_analysis_frame,
    text="Run Analysis",
    width=15,
    #command=lambda: tab3_controller.do_linear_analysis(
        #plot_frame_gait_analysis, gait_assume_walking_var
    #),
)
tab4_analysis_button.pack(side="left", padx=10)

tab4_assume_walking_check = make_checkbutton(
    stance_analysis_frame, text="Assume data is walking", variable=stance_assume_walking_var
)

tab4_assume_walking_check.pack(side="left", padx=(12, 12), pady=6, ipadx=4, ipady=4)

plot_frame_stance_analysis.pack(fill="both", expand=True)

tab4_save_button_frame = tk.Frame(tab4)
tab4_save_button_frame.pack(pady=5)

tab4_save_csv_button = make_action_button(
    tab4_save_button_frame,
    text="Save Analysis",
    #command=lambda: tab4_controller.save_linear_analysis(True),
)
tab4_save_csv_button.pack(side="left", padx=5)

tab4_save_plot_button = make_action_button(
    tab4_save_button_frame,
    text="Save Plot",
    #command=lambda: tab4_controller.save_plot(True),
)
tab4_save_plot_button.pack(side="left", padx=5)

tab4_save_all_output_button = make_action_button(
    tab4, text="Save All", #command=lambda: tab4_controller.save_all_output()
)
tab4_save_all_output_button.pack(pady=5)

# -------------------------Extra---------------------------------
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
    *tab5_controller.heavy_job_disable_widgets(),
    *tab2_gsd_algorithm_radios,
)

# -------------------------Running the GUI---------------------------------
root.mainloop()