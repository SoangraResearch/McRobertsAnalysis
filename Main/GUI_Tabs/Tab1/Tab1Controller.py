from __future__ import annotations

import os
import sys
import csv
import matplotlib.dates as mdates
import tkinter as tk
from tkinter import filedialog, messagebox
from OMX_To_CSV import (
    _resolve_octave_executable,
    matlab_datenum_to_datetime,
    process_omx_file,
)
from Main import app_config
from Main.GUI_Tabs.gui_style import (
    make_action_button,
    pointer_cursor,
    restore_main_window_focus,
)
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

        self._time_var_programmatic = False

        self._octave_path_var: tk.StringVar | None = None
        self._octave_label_frame: tk.LabelFrame | None = None
        self._octave_status_label: tk.Label | None = None
        self._octave_advanced_frame: tk.Frame | None = None
        self._octave_disclosure_row: tk.Frame | None = None
        self._octave_arrow_label: tk.Label | None = None
        self._octave_disclosure_text: tk.Label | None = None
        self._oct_manual_panel_open: bool = False

# -------------------------Public Methods---------------------------------

    def build_octave_section(self) -> None:
        """OMX requires GNU Octave; manual path only when auto-detect fails or user opens it."""
        lf = tk.LabelFrame(
            self.tab,
            text="GNU Octave (required for .OMX)",
            padx=8,
            pady=6,
        )
        lf.pack(fill=tk.X, padx=10, pady=(6, 4))
        self._octave_label_frame = lf

        self._octave_status_label = tk.Label(
            lf,
            text="",
            wraplength=900,
            justify=tk.LEFT,
        )
        self._octave_status_label.pack(anchor=tk.W, pady=(0, 2))

        self._octave_disclosure_row = tk.Frame(lf, cursor=pointer_cursor())
        self._octave_arrow_label = tk.Label(
            self._octave_disclosure_row,
            text="▶",
            fg="#d4dce8",
            cursor=pointer_cursor(),
            width=2,
            anchor="w",
        )
        self._octave_arrow_label.pack(side=tk.LEFT)
        self._octave_disclosure_text = tk.Label(
            self._octave_disclosure_row,
            text="Set path manually",
            fg="#d4dce8",
            cursor=pointer_cursor(),
        )
        self._octave_disclosure_text.pack(side=tk.LEFT, padx=(2, 0))
        for _w in (
            self._octave_disclosure_row,
            self._octave_arrow_label,
            self._octave_disclosure_text,
        ):
            _w.bind("<Button-1>", self._octave_toggle_disclosure)

        self._octave_advanced_frame = tk.Frame(lf)
        # Disclosure row + advanced frame packing is applied in _octave_apply_manual_panel_visibility().

        hint = tk.Label(
            self._octave_advanced_frame,
            text=(
                "Use this only if Octave was not found automatically. Set the full file path to "
                "Octave's command-line program: octave-cli on macOS/Linux (often Homebrew: "
                "/opt/homebrew/bin or /usr/local/bin) or octave-cli.exe inside your GNU Octave "
                "installation on Windows (typically a mingw64\\bin folder). Leave blank and save "
                "to clear a saved path and try auto-detect again."
            ),
            wraplength=900,
            justify=tk.LEFT,
        )
        hint.pack(anchor=tk.W, pady=(4, 4))

        row = tk.Frame(self._octave_advanced_frame)
        row.pack(fill=tk.X)
        tk.Label(row, text="File path:").pack(side=tk.LEFT)
        self._octave_path_var = tk.StringVar(
            value=str(app_config.current.get("octave_executable", "") or "")
        )
        self._octave_entry = tk.Entry(row, textvariable=self._octave_path_var)
        self._octave_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        btn_row = tk.Frame(self._octave_advanced_frame)
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

        resolved = _resolve_octave_executable()
        self._oct_manual_panel_open = resolved is None
        self._octave_apply_manual_panel_visibility()

        if self.heavy_job is not None:
            self.heavy_job.register_disable_widgets(
                self._octave_disclosure_row,
                self._octave_arrow_label,
                self._octave_disclosure_text,
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
            for name in ("_current_start_entry", "_current_stop_entry"):
                w = getattr(self, name, None)
                if w is not None:
                    try:
                        w.configure(state="normal")
                    except tk.TclError:
                        pass
            self._update_time_vars()
            start_dt, stop_dt = self.acceleration_plot.get_current_bounds()
            self.file_start_time.set(start_dt.strftime("%Y-%m-%d %H:%M:%S"))
            self.file_stop_time.set(stop_dt.strftime("%Y-%m-%d %H:%M:%S"))
            self.acceleration_plot.register_view_change_callback(self._update_time_vars)
            self.acceleration_plot.register_highlight_change_callback(
                self._on_highlight_export_range_changed
            )

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

            def on_omx_error(msg: str) -> None:
                if self._octave_error_suggests_path_issue(msg):
                    self._oct_manual_panel_open = True
                    self._octave_apply_manual_panel_visibility()
                messagebox.showerror("Load OMX failed", msg, parent=self.tab)

            self.heavy_job.run(
                "Loading OMX file…",
                load_omx_worker,
                on_success=apply_loaded,
                on_error=on_omx_error,
                deferred_finalize=True,
            )
        else:
            try:
                apply_loaded(process_omx_file(file_path))
            except Exception as e:
                msg = str(e)
                if self._octave_error_suggests_path_issue(msg):
                    self._oct_manual_panel_open = True
                    self._octave_apply_manual_panel_visibility()
                messagebox.showerror("Load OMX failed", msg, parent=self.tab)

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

    @staticmethod
    def _octave_error_suggests_path_issue(msg: str) -> bool:
        m = msg.lower()
        return any(
            k in m
            for k in (
                "octave",
                "oct2py",
                "octave-cli",
                "octave_executable",
                "gnu octave",
            )
        )

    def _octave_short_display_path(self, path: str, max_len: int = 88) -> str:
        p = path.replace("\\", "/")
        if len(p) <= max_len:
            return p
        head = max_len // 2 - 2
        tail = max_len - head - 3
        return f"{p[:head]}…{p[-tail:]}"

    def _octave_apply_manual_panel_visibility(self) -> None:
        if self._octave_status_label is None or self._octave_advanced_frame is None:
            return
        resolved = _resolve_octave_executable()
        show_manual = (resolved is None) or self._oct_manual_panel_open

        if resolved:
            self._octave_status_label.configure(
                text=(
                    "GNU Octave is ready to use.\n"
                    + self._octave_short_display_path(resolved)
                )
            )
        else:
            self._octave_status_label.configure(
                text=(
                    "GNU Octave was not found automatically. OMX needs Octave — set the full path "
                    "to octave-cli below, or install Octave (see Main/README.md)."
                )
            )

        try:
            self._octave_advanced_frame.pack_forget()
        except tk.TclError:
            pass
        if self._octave_disclosure_row is not None:
            try:
                self._octave_disclosure_row.pack_forget()
            except tk.TclError:
                pass

        if resolved is None:
            if show_manual:
                try:
                    self._octave_advanced_frame.pack(fill=tk.X, pady=(4, 0))
                except tk.TclError:
                    pass
            return

        dr = self._octave_disclosure_row
        ar = self._octave_arrow_label
        if dr is None or ar is None:
            return

        ar.configure(text="▼" if self._oct_manual_panel_open else "▶")
        dr.pack(anchor=tk.W, pady=(2, 0))
        if show_manual:
            try:
                self._octave_advanced_frame.pack(fill=tk.X, pady=(4, 0))
            except tk.TclError:
                pass

    def _octave_toggle_disclosure(self, _event=None) -> None:
        if _resolve_octave_executable() is None:
            return
        self._oct_manual_panel_open = not self._oct_manual_panel_open
        self._octave_apply_manual_panel_visibility()

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
        resolved = _resolve_octave_executable()
        self._oct_manual_panel_open = resolved is None
        self._octave_apply_manual_panel_visibility()

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
        if self.acceleration_plot is None:
            return
        if self.acceleration_plot.get_highlight_range() is not None:
            return
        start_dt, stop_dt = self.acceleration_plot.get_current_bounds()
        start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        stop_str = stop_dt.strftime('%Y-%m-%d %H:%M:%S')

        self.current_start_time.set(start_str)
        self.current_stop_time.set(stop_str)

    def _on_highlight_export_range_changed(self):
        if self.acceleration_plot is None:
            return
        r = self.acceleration_plot.get_highlight_range()
        if r is None:
            for name in ("_current_start_entry", "_current_stop_entry"):
                w = getattr(self, name, None)
                if w is not None:
                    try:
                        w.configure(state="normal")
                    except tk.TclError:
                        pass
            self._update_time_vars()
            return

        start_dt, stop_dt = r
        if start_dt.tzinfo is not None:
            start_dt = start_dt.replace(tzinfo=None)
        if stop_dt.tzinfo is not None:
            stop_dt = stop_dt.replace(tzinfo=None)

        fmt = "%Y-%m-%d %H:%M:%S"
        start_str = start_dt.strftime(fmt)
        stop_str = stop_dt.strftime(fmt)

        self._time_var_programmatic = True
        try:
            self.current_start_time.set(start_str)
            self.current_stop_time.set(stop_str)
        finally:
            self._time_var_programmatic = False

        start_num = mdates.date2num(start_dt)
        stop_num = mdates.date2num(stop_dt)
        self.acceleration_plot.zoom_to_bounds(start_num, stop_num)

        for name in ("_current_start_entry", "_current_stop_entry"):
            w = getattr(self, name, None)
            if w is not None:
                try:
                    w.configure(state="readonly")
                except tk.TclError:
                    pass

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
        if self._time_var_programmatic:
            return
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