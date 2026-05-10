"""Auto-Analysis tab: OMX → day chunks → GSD, segment batch, CSV export."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

from Main import app_config
from OMX_To_CSV import process_omx_file
from Main.GUI_Tabs.Tab4.auto_analysis_progress import auto_analysis_progress
from Main.GUI_Tabs.Tab4.Auto_analysis_code import (
    SegmentBatchCancelled,
    combine_segment_batch_results_to_tables,
    count_steps_per_chunk,
    run_segment_batch_analysis,
    run_sequence_detection_per_chunk,
    select_one_segment_per_chunk,
    split_data_by_day,
)
from Main.GUI_Tabs.gui_style import (
    make_action_button,
    make_checkbutton,
    make_radiobutton,
    restore_main_window_focus,
)
from Main.GUI_Tabs.heavy_job_runner import HEAVY_JOB_CANCELLED


class Tab4Controller:
    def __init__(self, tab_frame, heavy_job=None):
        self.tab = tab_frame
        self.heavy_job = heavy_job

        self.auto_analysis_file = "None"
        self.auto_analysis_per_chunk_results = None
        self.auto_analysis_selected_segments = None
        self.auto_analysis_batch_results = None

        self.load_omx_button = None
        self.force_walking_check = None
        self.run_linear_check = None
        self.run_nonlinear_check = None
        self.run_analysis_button = None
        self.gsd_algorithm_radios = []

        self._build_ui()

    def heavy_job_disable_widgets(self):
        return (
            self.load_omx_button,
            self.force_walking_check,
            self.run_linear_check,
            self.run_nonlinear_check,
            self.run_analysis_button,
            *self.gsd_algorithm_radios,
        )

    @staticmethod
    def _resolve_output_folder_path(chosen_path):
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

    def load_auto_analysis_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("OMX file", "*.OMX")])
        restore_main_window_focus(self.tab)
        if not file_path:
            return
        auto_analysis_filename = os.path.splitext(os.path.basename(file_path))[0]
        try:
            if file_path.endswith(".OMX"):
                messagebox.showinfo("Loaded", f"Loaded file:\n{file_path}")
                self.auto_analysis_file = file_path
                self.auto_analysis_path_var.set(f"File loaded: {auto_analysis_filename}")
            else:
                raise ValueError("Unsupported file format")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def run_auto_analysis(self):
        heavy_job = self.heavy_job
        if heavy_job is None:
            messagebox.showerror("Error", "Job runner not available.")
            return

        if self.auto_analysis_file == "None":
            messagebox.showerror("Error", "File not loaded")
            return

        if self.label_var_auto_analysis.get() == "None":
            messagebox.showerror("Error", "GSD algorithm not set")
            return

        do_linear = self.run_linear_var.get()
        do_nonlinear = self.run_nonlinear_var.get()
        if not do_linear and not do_nonlinear:
            messagebox.showerror(
                "Error", "Select at least one analysis to run (Linear or Nonlinear)."
            )
            return

        file_path = self.auto_analysis_file
        gsd_type = self.label_var_auto_analysis.get()
        force_walk = self.force_data_as_walking_tab4.get()

        self.progress_text.clear()

        def sync_tab4_canvas(step_name: str) -> None:
            def apply() -> None:
                self.progress_text.update_progress(step_name)

            heavy_job.schedule_main(apply)

        def notify_status(msg: str) -> None:
            heavy_job.schedule_status_message(f"Auto analysis: {msg}")

        class _AutoOmxCancelled(Exception):
            pass

        def _omx_progress_cancel(_p: int, _chunk: int = 0, _total: int = 0) -> None:
            if heavy_job.is_cancel_requested():
                raise _AutoOmxCancelled()

        def worker():
            if heavy_job.is_cancel_requested():
                return HEAVY_JOB_CANCELLED

            cfg = app_config.current["auto_analysis"]
            sample_seconds = cfg["sample_seconds"]
            random_seed = cfg["random_seed"]

            sync_tab4_canvas("Reading Data")
            notify_status("Reading OMX file…")
            try:
                auto_analysis_data, _filename = process_omx_file(
                    file_path, progress=_omx_progress_cancel
                )
            except _AutoOmxCancelled:
                return HEAVY_JOB_CANCELLED
            if heavy_job.is_cancel_requested():
                return HEAVY_JOB_CANCELLED
            timestamps = auto_analysis_data["ACC"][:, 0]

            sync_tab4_canvas("Splitting Data")
            notify_status("Splitting data by day…")
            data_chunks = split_data_by_day(auto_analysis_data, timestamps)
            if heavy_job.is_cancel_requested():
                return HEAVY_JOB_CANCELLED

            sync_tab4_canvas("Sequence Detection")
            notify_status("Sequence detection (GSD per day chunk)…")
            per_chunk = run_sequence_detection_per_chunk(
                data_chunks,
                gsd_type,
                force_walk,
                min_segment_seconds=sample_seconds,
            )
            if heavy_job.is_cancel_requested():
                return HEAVY_JOB_CANCELLED

            sync_tab4_canvas("Segment Selection")
            notify_status("Selecting random sample per day…")
            selection_records = select_one_segment_per_chunk(
                per_chunk, sample_seconds, random_seed
            )
            if heavy_job.is_cancel_requested():
                return HEAVY_JOB_CANCELLED

            sync_tab4_canvas("Segment Analysis")
            try:
                batch_results = run_segment_batch_analysis(
                    data_chunks,
                    selection_records,
                    assume_walking=True,
                    do_linear=do_linear,
                    do_nonlinear=do_nonlinear,
                    progress_callback=notify_status,
                    cancel_check=heavy_job.is_cancel_requested,
                )
            except SegmentBatchCancelled:
                return HEAVY_JOB_CANCELLED
            if heavy_job.is_cancel_requested():
                return HEAVY_JOB_CANCELLED

            sync_tab4_canvas("Output")
            notify_status("Combining results…")
            n_ok_chunks = sum(1 for r in selection_records if r["reason"] == "ok")
            n_ok = sum(1 for r in batch_results if r.get("error") is None)
            n_fail = len(batch_results) - n_ok
            linear_all_df, nonlinear_all_df, _failures = (
                combine_segment_batch_results_to_tables(batch_results)
            )

            steps_per_chunk = count_steps_per_chunk(per_chunk)
            total_steps = sum(steps_per_chunk)

            return {
                "per_chunk": per_chunk,
                "selection_records": selection_records,
                "batch_results": batch_results,
                "n_chunks": len(data_chunks),
                "n_ok_chunks": n_ok_chunks,
                "n_ok": n_ok,
                "n_fail": n_fail,
                "sample_seconds": sample_seconds,
                "steps_per_chunk": steps_per_chunk,
                "total_steps": total_steps,
                "linear_all_df": linear_all_df,
                "nonlinear_all_df": nonlinear_all_df,
                "base_dir": os.path.dirname(file_path),
                "base_name": os.path.splitext(os.path.basename(file_path))[0],
            }

        def on_success(payload):
            self.auto_analysis_per_chunk_results = payload["per_chunk"]
            self.auto_analysis_selected_segments = payload["selection_records"]
            self.auto_analysis_batch_results = payload["batch_results"]

            linear_all_df = payload["linear_all_df"]
            nonlinear_all_df = payload["nonlinear_all_df"]
            n_ok_chunks = payload["n_ok_chunks"]
            n_ok = payload["n_ok"]
            n_fail = payload["n_fail"]
            data_chunks_len = payload["n_chunks"]
            sample_seconds = payload["sample_seconds"]
            selection_records = payload["selection_records"]
            steps_per_chunk = payload["steps_per_chunk"]
            total_steps = payload["total_steps"]
            base_dir = payload["base_dir"]
            base_name = payload["base_name"]

            want_linear = not linear_all_df.empty
            want_nonlinear = not nonlinear_all_df.empty
            anything_to_save = want_linear or want_nonlinear

            saved_any = False
            saved_paths = []
            output_dir = None
            root = self.tab.winfo_toplevel()
            if anything_to_save:
                chosen = filedialog.asksaveasfilename(
                    initialdir=base_dir,
                    initialfile=f"{base_name}_AutoAnalysis",
                    title="Save Auto-Analysis output folder",
                    defaultextension="",
                    filetypes=[("All files", "*.*")],
                )
                restore_main_window_focus(root)
                output_dir = self._resolve_output_folder_path(chosen)
                if output_dir:
                    try:
                        os.makedirs(output_dir, exist_ok=True)
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

            step_lines = [
                f"  Day {i + 1}: {steps_per_chunk[i]}"
                for i in range(len(steps_per_chunk))
            ]
            step_block = (
                f"Total steps detected: {total_steps}\n"
                + "\n".join(step_lines)
                + "\n\n"
            )

            chunk_lines = []
            for rec in selection_records:
                day_num = rec["chunk_index"] + 1
                if rec["reason"] == "ok":
                    seg = rec["segment"]
                    chunk_lines.append(
                        f"  Day {day_num}: {sample_seconds} s sample"
                        f" @ {seg['Start']:.1f}\u2013{seg['End']:.1f} s"
                    )
                else:
                    chunk_lines.append(
                        f"  Day {day_num}: skipped ({rec['reason']})"
                    )

            all_skipped = n_ok_chunks == 0
            summary_msg = step_block + (
                f"Day chunks: {data_chunks_len}\n"
                f"Chunks with sample: {n_ok_chunks}\n"
                f"Analyzed OK: {n_ok}, failed: {n_fail}\n"
            )
            if chunk_lines:
                summary_msg += "\n".join(chunk_lines) + "\n"

            if saved_any:
                summary_msg += "\nSaved to folder:\n" + output_dir + "\n\nFiles:\n" + "\n".join(
                    os.path.basename(p) for p in saved_paths
                )
            else:
                if all_skipped:
                    summary_msg += (
                        "\nNo walking samples found in any day chunk"
                        f" (no bouts \u2265 {sample_seconds} s)."
                    )
                elif not anything_to_save:
                    summary_msg += "\nNo CSV outputs to write (all tables empty)."
                elif not output_dir:
                    summary_msg += "\nNo CSVs saved (output location cancelled)."
                else:
                    summary_msg += "\nNo CSVs saved."

            messagebox.showinfo("Auto Analysis", summary_msg)
            self.progress_text.clear()

        def on_error(msg: str):
            self.auto_analysis_per_chunk_results = None
            self.auto_analysis_selected_segments = None
            self.auto_analysis_batch_results = None
            self.progress_text.clear()
            messagebox.showerror("Auto Analysis Error", msg)

        if not heavy_job.run(
            "Auto analysis…",
            worker,
            on_success=on_success,
            on_error=on_error,
        ):
            return

    def _build_ui(self):
        self.load_omx_button = make_action_button(
            self.tab, text="Load OMX File", command=self.load_auto_analysis_file
        )
        self.load_omx_button.pack(pady=10)

        self.auto_analysis_path_var = tk.StringVar(value="File loaded: (none)")
        auto_analysis_file_label = tk.Label(self.tab, textvariable=self.auto_analysis_path_var)
        auto_analysis_file_label.pack()

        self.label_var_auto_analysis = tk.StringVar()
        self.label_var_auto_analysis.set("None")
        tk.Label(self.tab, text="Select Type").pack(pady=(20, 5))
        label_frame = tk.Frame(self.tab)
        label_frame.pack(pady=(0, 4))
        self.gsd_algorithm_radios = []
        for lbl in ["Healthy(GSDA)", "Patient(GSDB)"]:
            rb = make_radiobutton(
                label_frame, text=lbl, variable=self.label_var_auto_analysis, value=lbl
            )
            rb.pack(side="left", padx=(16, 16), pady=8, ipadx=4, ipady=4)
            self.gsd_algorithm_radios.append(rb)

        self.force_data_as_walking_tab4 = tk.BooleanVar(value=False)
        self.force_walking_check = make_checkbutton(
            self.tab, text="Force Data as Walking", variable=self.force_data_as_walking_tab4
        )
        self.force_walking_check.pack(pady=(10, 6), ipadx=4, ipady=4)

        self.run_linear_var = tk.BooleanVar(value=True)
        self.run_linear_check = make_checkbutton(
            self.tab, text="Run Linear analysis", variable=self.run_linear_var
        )
        self.run_linear_check.pack(pady=(2, 2), ipadx=4, ipady=4)

        self.run_nonlinear_var = tk.BooleanVar(value=True)
        self.run_nonlinear_check = make_checkbutton(
            self.tab, text="Run Nonlinear analysis", variable=self.run_nonlinear_var
        )
        self.run_nonlinear_check.pack(pady=(2, 6), ipadx=4, ipady=4)

        self.run_analysis_button = make_action_button(
            self.tab, text="Run Auto Analysis", command=self.run_auto_analysis
        )
        self.run_analysis_button.pack(pady=10)

        self.progress_text = auto_analysis_progress(self.tab, font_size=10)
        self.progress_text.clear()
