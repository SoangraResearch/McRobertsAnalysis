import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from Main.OMX_To_CSV import process_omx_file
from Main.Acceleration_Plot import PlotOMX

#setting directory properly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# -------------------------Tkinter Setup---------------------------------

# Create the main window
root = tk.Tk()
root.title("McRoberts Analysis")
root.geometry("1000x600")

tab_control = ttk.Notebook(root)
tab1 = tk.Frame(tab_control)
tab_control.add(tab1, text="Select Data") #First Tab

plot_frame = None

tab_control.pack(expand=1, fill='both')

# Global variables
# selected_file = None
# extracted_df = None
start_time_var = tk.StringVar()
stop_time_var = tk.StringVar()
file_start_time_var = tk.StringVar()
file_stop_time_var = tk.StringVar()
label_var = tk.StringVar()
export_format_var = tk.StringVar()

# -------------------------Methods---------------------------------
def load_file():
    global selected_file #, extracted_df

    file_path = filedialog.askopenfilename(filetypes=[("OMX file", "*.OMX")])
    if not file_path:
        return
    
    selected_file = file_path

    data, filename, file_start_time, file_stop_time = process_omx_file(selected_file)

    # Update non-editable display
    file_start_time_var.set(file_start_time)
    file_stop_time_var.set(file_stop_time)

    # Set defaults for editable fields
    start_time_var.set(file_start_time)
    stop_time_var.set(file_stop_time)

    acceleration_plot = PlotOMX(data, filename, plot_frame)

    #TODO: ensure time consistency
    #TODO: integrate GSD into main plot?
    #TODO: csv exporting

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

# -------------------------Tab 1 Select Data---------------------------------

load_file_button = tk.Button(tab1, text="Load OMX File", command=load_file)
load_file_button.pack(pady=10)

load_time_entries()

plot_frame = tk.Frame(tab1, height=350)
plot_frame.pack(fill="both", expand=True)
plot_frame.pack_propagate(False)

button_frame = tk.Frame(tab1)
button_frame.pack(pady=10)

Export_Button = tk.Button(button_frame, text="Export To CSV", command=None)
Export_Button.pack()

# -------------------------Running the GUI---------------------------------
root.mainloop()