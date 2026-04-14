from __future__ import annotations

import os
import sys
import csv
import matplotlib.dates as mdates
import tkinter as tk
from tkinter import filedialog, messagebox
from OMX_To_CSV import process_omx_file, matlab_datenum_to_datetime
from Main import app_config
from Main.GUI_Tabs.gui_style import make_action_button, restore_main_window_focus
from Main.GUI_Tabs.heavy_job_runner import HEAVY_JOB_CANCELLED
from Main.GUI_Tabs.Tab1.Acceleration_Plot import PlotOMX
from datetime import datetime

# OMX Octave read vs acceleration-plot prep: bar share (plot phase is usually shorter).
_OMX_LOAD_PROGRESS_SHARE = 85


class _OmxLoadCancelled(Exception):
    """Propagates cooperative cancel out of OMX progress callbacks."""

    pass

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

        self._octave_path_var: tk.StringVar | None = None

# -------------------------Public Methods---------------------------------

    def build_octave_section(self) -> None:
        """OMX requires GNU Octave; let users persist octave-cli path (frozen .exe / minimal PATH)."""
        lf = tk.LabelFrame(
            self.tab,
            text="GNU Octave (required for .OMX)",
            padx=8,
            pady=6,
        )
        lf.pack(fill=tk.X, padx=10, pady=(6, 4))

        hint = tk.Label(
            lf,
            text=(
                "Leave blank to auto-detect. If OMX fails to load, set the full file path to Octave's "
                "command-line program: octave-cli on macOS/Linux (often Homebrew: /opt/homebrew/bin or "
                "/usr/local/bin) or octave-cli.exe inside your GNU Octave installation on Windows "
                "(typically a mingw64\\bin folder)."
            ),
            wraplength=900,
            justify=tk.LEFT,
        )
        hint.pack(anchor=tk.W, pady=(0, 4))

        row = tk.Frame(lf)
        row.pack(fill=tk.X)
        tk.Label(row, text="File path:").pack(side=tk.LEFT)
        self._octave_path_var = tk.StringVar(
            value=str(app_config.current.get("octave_executable", "") or "")
        )
        self._octave_entry = tk.Entry(row, textvariable=self._octave_path_var)
        self._octave_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        btn_row = tk.Frame(lf)
        btn_row.pack(fill=tk.X, pady=(6, 0))

        self._octave_browse_btn = make_action_button(
            btn_row, text="Browse…", command=self._octave_browse
        )
        self._octave_browse_btn.pack(side=tk.LEFT, padx=(0, 6))

        self._octave_save_btn = make_action_button(
            btn_row, text="Save path", command=self._octave_save_path
        )
        self._octave_save_btn.pack(side=tk.LEFT, padx=(0, 6))

        self._octave_clear_btn = make_action_button(
            btn_row, text="Clear (auto-detect)", command=self._octave_clear_path
        )
        self._octave_clear_btn.pack(side=tk.LEFT)

        if self.heavy_job is not None:
            self.heavy_job.register_disable_widgets(
                self._octave_entry,
                self._octave_browse_btn,
                self._octave_save_btn,
                self._octave_clear_btn,
            )

    def load_file(self, plot_frame_OMX):
        file_path = filedialog.askopenfilename(filetypes=[("OMX file", "*.OMX")])
        restore_main_window_focus(self.tab)
        if not file_path:
            return

        def apply_loaded(result):
            self.data, self.filename = result
            n_samples = len(self.data["ACC"])
            share = _OMX_LOAD_PROGRESS_SHARE

            if self.heavy_job is not None:
                self.heavy_job.set_busy_base_message("Building acceleration plot…")
                self.heavy_job.schedule_progress(share)

                def plot_progress(p: int) -> None:
                    self.heavy_job.schedule_progress(
                        share + int(p * (100 - share) / 100)
                    )

                plot_kw = {"progress": plot_progress}
            else:
                plot_kw = {}

            self.acceleration_plot = PlotOMX(
                self.data, self.filename, plot_frame_OMX, **plot_kw
            )
            self._update_time_vars()
            start_dt, stop_dt = self.acceleration_plot.get_current_bounds()
            self.file_start_time.set(start_dt.strftime("%Y-%m-%d %H:%M:%S"))
            self.file_stop_time.set(stop_dt.strftime("%Y-%m-%d %H:%M:%S"))
            self.acceleration_plot.register_view_change_callback(self._update_time_vars)

            if self.heavy_job is not None:
                self.heavy_job.release_success(
                    f"✓ Loaded {n_samples:,} samples", flash_ms=7000
                )

        if self.heavy_job:
            def omx_progress(p: int, chunk: int = 0, total: int = 0) -> None:
                if self.heavy_job.is_cancel_requested():
                    raise _OmxLoadCancelled()
                if chunk and total:
                    self.heavy_job.set_busy_base_message(
                        f"Reading OMX data… chunk {chunk}/{total}"
                    )
                self.heavy_job.schedule_progress(
                    int(p * _OMX_LOAD_PROGRESS_SHARE / 100)
                )

            def load_omx_worker():
                try:
                    return process_omx_file(file_path, progress=omx_progress)
                except _OmxLoadCancelled:
                    return HEAVY_JOB_CANCELLED

            self.heavy_job.run(
                "Loading OMX file…",
                load_omx_worker,
                on_success=apply_loaded,
                deferred_finalize=True,
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
                    if self.heavy_job is not None and self.heavy_job.is_cancel_requested():
                        return HEAVY_JOB_CANCELLED
                    writer.writerow(row)
                    percent_complete = int(i / total_rows * 100)
                    if percent_complete // 10 > last_reported_percent // 10:
                        last_reported_percent = percent_complete
                        print(f"{(percent_complete // 10) * 10}% converted...")
            return {"status": "ok", "path": output_path}

        def on_csv_done(payload):
            if payload is HEAVY_JOB_CANCELLED:
                return
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

    def _octave_browse(self) -> None:
        if self._octave_path_var is None:
            return
        if sys.platform == "win32":
            filetypes = [
                ("Octave CLI", "octave-cli.exe"),
                ("Executable", "*.exe"),
                ("All files", "*.*"),
            ]
        else:
            filetypes = [("All files", "*")]
        cur = (self._octave_path_var.get() or "").strip()
        initialdir = os.path.dirname(cur) if cur and os.path.isfile(cur) else None
        path = filedialog.askopenfilename(
            title="Select GNU Octave CLI (file path)",
            filetypes=filetypes,
            initialdir=initialdir,
        )
        restore_main_window_focus(self.tab)
        if path:
            self._octave_path_var.set(path)

    def _octave_clear_path(self) -> None:
        if self._octave_path_var is None:
            return
        self._octave_path_var.set("")

    def _octave_save_path(self) -> None:
        if self._octave_path_var is None:
            return
        raw = (self._octave_path_var.get() or "").strip()
        if raw and not os.path.isfile(raw):
            messagebox.showerror(
                "Octave path",
                f"File not found:\n{raw}",
                parent=self.tab,
            )
            return
        app_config.current["octave_executable"] = raw
        try:
            app_config.save(app_config.current)
        except OSError as e:
            messagebox.showerror("Save failed", str(e), parent=self.tab)
            return
        messagebox.showinfo(
            "Octave path",
            "Saved. OMX will use this path on the next load.",
            parent=self.tab,
        )

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