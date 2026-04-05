import os
import csv
import matplotlib.dates as mdates
import tkinter as tk
from tkinter import filedialog, messagebox
from OMX_To_CSV import process_omx_file, matlab_datenum_to_datetime
from Main.GUI_Tabs.gui_style import restore_main_window_focus
from Main.GUI_Tabs.Tab1.Acceleration_Plot import PlotOMX
from datetime import datetime

class Tab1Controller:
    def __init__(self, tab_frame, heavy_job=None):
        self.tab = tab_frame
        self.heavy_job = heavy_job

        self.data = None
        self.filename = None
        self.acceleration_plot = None

        #name of exported file, including stimestamps
        self.export_filename = None

        #Folder file is exported to
        self.export_folder = None
        
        #current bounds of plot
        self.current_start_time = tk.StringVar()
        self.current_stop_time = tk.StringVar()

        #maximum bounds of plot/data
        self.file_start_time = tk.StringVar()
        self.file_stop_time = tk.StringVar()

# -------------------------Public Methods---------------------------------

    def load_file(self, plot_frame_OMX):
        file_path = filedialog.askopenfilename(filetypes=[("OMX file", "*.OMX")])
        restore_main_window_focus(self.tab)
        if not file_path:
            return

        def apply_loaded(result):
            self.data, self.filename = result
            self.acceleration_plot = PlotOMX(self.data, self.filename, plot_frame_OMX)
            self._update_time_vars()
            start_dt, stop_dt = self.acceleration_plot.get_current_bounds()
            self.file_start_time.set(start_dt.strftime("%Y-%m-%d %H:%M:%S"))
            self.file_stop_time.set(stop_dt.strftime("%Y-%m-%d %H:%M:%S"))
            self.acceleration_plot.register_view_change_callback(self._update_time_vars)

        if self.heavy_job:
            self.heavy_job.run(
                "Loading OMX file…",
                lambda: process_omx_file(file_path),
                on_success=apply_loaded,
            )
        else:
            apply_loaded(process_omx_file(file_path))

    def create_time_labels(self):
        self._create_max_time_labels()
        self._create_current_time_labels()

    def export_csv(self, after_export=None):
        if self.data is None:
            messagebox.showerror("Error", "No data loaded.")
            return False

        self._create_tab1_export_folder()

        output_path = self._get_csv_output_path()
        if not output_path:
            return False

        starttime = datetime.strptime(self.current_start_time.get(), "%Y-%m-%d %H:%M:%S")
        stoptime = datetime.strptime(self.current_stop_time.get(), "%Y-%m-%d %H:%M:%S")
        acc_data = self.data["ACC"]

        def write_csv_worker():
            filtered_rows = [
                row
                for row in acc_data
                if starttime <= matlab_datenum_to_datetime(row[0]) <= stoptime
            ]
            if len(filtered_rows) == 0:
                return {"status": "empty"}
            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow(["Time", "Ax", "Ay", "Az"])
                total_rows = len(filtered_rows)
                last_reported_percent = 0
                for i, row in enumerate(filtered_rows, start=1):
                    writer.writerow(row)
                    percent_complete = int(i / total_rows * 100)
                    if percent_complete // 10 > last_reported_percent // 10:
                        last_reported_percent = percent_complete
                        print(f"{(percent_complete // 10) * 10}% converted...")
            return {"status": "ok", "path": output_path}

        def on_csv_done(payload):
            if payload["status"] == "empty":
                messagebox.showinfo("Info", "No data in the specified time range.")
            else:
                messagebox.showinfo("Success", f"File saved to:\n{payload['path']}")
                if after_export:
                    after_export()

        if self.heavy_job:
            return self.heavy_job.run(
                "Exporting CSV…",
                write_csv_worker,
                on_success=on_csv_done,
            )

        try:
            payload = write_csv_worker()
            on_csv_done(payload)
            return payload["status"] == "ok"
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")
            return False

    def export_acceleration_plot(self):
        if self.acceleration_plot is None:
            messagebox.showerror("Error", "No acceleration plot to export.")
            return

        self._create_tab1_export_folder()

        output_path = self._get_plot_output_path()
        if not output_path:
            return

        def save_on_main(path):
            try:
                self.acceleration_plot.fig.savefig(path, dpi=300)
                messagebox.showinfo("Success", f"File saved to:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")

        if self.heavy_job:
            self.heavy_job.run(
                "Saving acceleration plot…",
                lambda p=output_path: p,
                on_success=save_on_main,
            )
        else:
            save_on_main(output_path)
    
# -------------------------Private/Helper Methods---------------------------------

    def _register_busy_lock_entries(self) -> None:
        if self.heavy_job is None:
            return
        self.heavy_job.register_disable_widgets(
            self._file_start_entry,
            self._file_stop_entry,
            self._current_start_entry,
            self._current_stop_entry,
        )

    def _update_time_vars(self):
        if self.acceleration_plot is not None:
            start_dt, stop_dt = self.acceleration_plot.get_current_bounds()
            start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
            stop_str = stop_dt.strftime('%Y-%m-%d %H:%M:%S')
            
            self.current_start_time.set(start_str)
            self.current_stop_time.set(stop_str)
        
    def _create_max_time_labels(self):
        # Outer frame to hold min start and stop time
        time_frame = tk.Frame(self.tab)
        time_frame.pack(pady=10)

        # Start time group
        start_group = tk.Frame(time_frame)
        start_group.pack(side="left", padx=40)

        tk.Label(start_group, text="File Start Time:", width=32, anchor='center').pack()
        self._file_start_entry = tk.Entry(
            start_group, textvariable=self.file_start_time, state="readonly", width=20
        )
        self._file_start_entry.pack()

        # Stop time group
        stop_group = tk.Frame(time_frame)
        stop_group.pack(side="left", padx=40)

        tk.Label(stop_group, text="File Stop Time:", width=32, anchor='center').pack()
        self._file_stop_entry = tk.Entry(
            stop_group, textvariable=self.file_stop_time, state="readonly", width=20
        )
        self._file_stop_entry.pack()

    def _create_current_time_labels(self):
        #frame for current start and stop time
        current_time_frame = tk.Frame(self.tab)
        current_time_frame.pack(pady=10)

        #current time group
        current_start_group = tk.Frame(current_time_frame)
        current_start_group.pack(side="left", padx=40)

        tk.Label(current_start_group, text="Start Time (YYYY-MM-DD HH:MM:SS):", width=32, anchor='w').pack()
        self._current_start_entry = tk.Entry(current_start_group, textvariable=self.current_start_time)
        self._current_start_entry.pack()

        # Stop time group
        current_stop_group = tk.Frame(current_time_frame)
        current_stop_group.pack(side="left", padx=40)

        tk.Label(current_stop_group, text="Stop Time (YYYY-MM-DD HH:MM:SS):", width=32, anchor='w').pack()
        self._current_stop_entry = tk.Entry(current_stop_group, textvariable=self.current_stop_time)
        self._current_stop_entry.pack()

        #adding label updating
        self.current_start_time.trace_add("write", self._on_time_var_changed)
        self.current_stop_time.trace_add("write", self._on_time_var_changed)

        self._register_busy_lock_entries()

    def _on_time_var_changed(self, *args):
        if self.acceleration_plot is not None:
            start_val = self.current_start_time.get()
            stop_val = self.current_stop_time.get()

            if not start_val or not stop_val:
                return

            start_dt = datetime.strptime(start_val, '%Y-%m-%d %H:%M:%S')
            stop_dt = datetime.strptime(stop_val, '%Y-%m-%d %H:%M:%S')
            
            start_num = mdates.date2num(start_dt)
            stop_num = mdates.date2num(stop_dt)

            self.acceleration_plot.zoom_to_bounds(start_num, stop_num)

    def _create_tab1_export_folder(self):
        safe_start = self.current_start_time.get().replace(":", "-").replace(" ", "_")
        safe_stop = self.current_stop_time.get().replace(":", "-").replace(" ", "_")

        self.export_filename = self.filename + "_from_" + safe_start + "_to_" + safe_stop

        self.export_folder = os.path.join(os.getcwd(), "../Data/Output/" + self.filename + "/" + self.export_filename)
        os.makedirs(self.export_folder, exist_ok=True)

    def _get_csv_output_path(self):
        output_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir=self.export_folder,
            initialfile=self.export_filename,
            title="Save CSV File"
            )
        restore_main_window_focus(self.tab)
        return output_path
    
    def _get_plot_output_path(self):
        output_path=filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf"), ("SVG File", "*.svg")],
            initialdir=self.export_folder,
            initialfile=self.export_filename + "_acceleration_plot",
            title="Save Acceleration Plot"
        )
        restore_main_window_focus(self.tab)
        return output_path