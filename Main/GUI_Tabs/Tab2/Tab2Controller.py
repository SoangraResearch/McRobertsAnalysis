import os
import pandas as pd
import numpy as np
from tkinter import filedialog, messagebox
from OMX_To_CSV import matlab_datenum_to_datetime
from GSDA_code import gsd_iluz
from GSDB_code import gsd_low_back_acc
from Main.GUI_Tabs.Tab2.GSD_plots import plot_GSDA, plot_GSDB, plot_steps
from ICDA_code import filter_and_print_long_segments, step_detection

class Tab2Controller:
    def __init__(self, tab_frame):
        self.tab = tab_frame

        #files
        self.file = None
        self.directory_path = None
        self.filename = None

        #controls for gsd processing
        self.force_data_as_walking = False

        #plot frames
        self.left_frame = None
        self.right_frame = None

        #raw df
        self.df = None

        #results
        self.sd_result_df = None
        self.gsd_plot = None
        self.step_result_df = None
        self.steps_plot = None

# -------------------------Public Methods---------------------------------

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV/JSON files", "*.csv *.json")])
        if not file_path:
            return

        try:
            if file_path.endswith(".csv"):
                messagebox.showinfo("Loaded", f"Loaded file:\n{file_path}")

                self.set_file(file_path)
        
                file_path = (f"File loaded: {self.filename}")
                return file_path
            else:
                raise ValueError("Unsupported file format")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))
            return "None"
        
    def set_file(self, file_path):
        self.file = file_path
        self.directory_path = os.path.dirname(file_path)
        self.filename = os.path.splitext(os.path.basename(file_path))[0]

    def process_GSD(self, GSDType, force_walking, left_GSD_frame, right_GSD_frame, extra_plots=0):  
        self._convert_mobiliseD_file_to_df()
        
        self.force_data_as_walking = force_walking
        self.left_frame = left_GSD_frame
        self.right_frame = right_GSD_frame

        try:
            acc = self.df.iloc[:, 1:4].to_numpy()
            time_col = self.df['Time'].to_numpy()
            original_time_array = [matlab_datenum_to_datetime(t) for t in time_col]
            fs = 100 #100 is proper amount for a mcroberts sensor

            if GSDType == "Healthy(GSDA)":
                gsd_result, v_acc_for_plot = self._run_GSDA(acc, fs, original_time_array)
            elif GSDType == "Patient(GSDB)":
                gsd_result, v_acc_for_plot = self._run_GSDB(acc, fs, original_time_array, extra_plots=extra_plots)
            else:
                gsd_result = -1

            self.sd_result_df = pd.DataFrame(gsd_result)
            step_result = step_detection(acc, gsd_result, fs, plot_results=False, original_time_array=original_time_array)
            self.step_result_df = pd.DataFrame(step_result)
            self.steps_plot = plot_steps(gsd_result, fs, v_acc_for_plot, self.right_frame)
            messagebox.showinfo("GSD Result", f"Gait sequences found: {len(gsd_result)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_GSD_results(self, open_prompt_window):
        try:
            if self.sd_result_df is None:
                messagebox.showerror("Error", "No GSD result to save.")
                return
            if open_prompt_window:
                output_path = self._get_csv_output_path("_GSD_results", "Save GSD results")
                if not output_path:
                    return False
            else:
                output_path = os.path.join(self.directory_path, self.filename + "_GSD_results.csv")

            self.sd_result_df.to_csv(output_path, index=False)
            messagebox.showinfo("Saved", f"GSD result saved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_GSD_plot(self, open_prompt_window):
        try:
            if self.gsd_plot is None:
                messagebox.showerror("Error", "No GSD plot to save.")
                return
            if open_prompt_window:
                output_path = self._get_plot_output_path("_GSD_plot", "Save GSD plot")
                if not output_path:
                    return False
            else:
                output_path = os.path.join(self.directory_path, self.filename + "_GSD_plot.png")

            self.gsd_plot.savefig(output_path, dpi=300)
            messagebox.showinfo("Saved", f"GSD plot saved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_step_counts(self, open_prompt_window):
        try:
            if self.step_result_df is None:
                messagebox.showerror("Error", "No step counts to save.")
                return
            if open_prompt_window:
                output_path = self._get_csv_output_path("_step_counts", "Save Step Counts")
                if not output_path:
                    return False
            else:
                output_path = os.path.join(self.directory_path, self.filename + "_step_counts.csv")

            self.step_result_df.to_csv(output_path, index=False)
            messagebox.showinfo("Saved", f"step counts saved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_steps_plot(self, open_prompt_window):
        try:
            if self.steps_plot is None:
                messagebox.showerror("Error", "No steps plot to save.")
                return
            if open_prompt_window:
                output_path = self._get_plot_output_path("_steps_plot", "Save Steps Plot")
                if not output_path:
                    return False
            else:
                output_path = os.path.join(self.directory_path, self.filename + "_steps_plot.png")

            self.steps_plot.savefig(output_path, dpi=300)
            messagebox.showinfo("Saved", f"steps plot saved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_all_GSD(self):
        try:
            self.save_GSD_results(False)
            self.save_GSD_plot(False)
            self.save_step_counts(False)
            self.save_steps_plot(False)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

# -------------------------Private/Helper Methods---------------------------------

    def _convert_mobiliseD_file_to_df(self):
        try:
            self.df = pd.read_csv(self.file)
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def _run_GSDA(self, acc, fs, original_time_array):
        imu_input = {"LowerBack": {"Acc": acc, "Gyr": np.zeros_like(acc), "Fs": {"Acc": fs}}}
        gsd_result, gait_bool_for_plot, v_acc_for_plot = gsd_iluz(imu_input, time_vector=original_time_array, plot_results=False, force_walking=self.force_data_as_walking)
        self.gsd_plot = plot_GSDA(gait_bool_for_plot, v_acc_for_plot, self.left_frame)
        long_segments = filter_and_print_long_segments(gsd_result, original_time_array=original_time_array, min_duration=30)
        return gsd_result, v_acc_for_plot

    def _run_GSDB(self, acc, fs, original_time_array, extra_plots=0):
        gsd_result, sig_det_act_for_plot, walk_label_for_plot = gsd_low_back_acc(acc, fs, plot_results=False, time_vector=original_time_array, force_walking=self.force_data_as_walking, extra_plots=extra_plots)
        v_acc_for_plot = np.linalg.norm(acc, axis=1)
        self.gsd_plot = plot_GSDB(sig_det_act_for_plot, walk_label_for_plot, self.left_frame)
        long_segments = filter_and_print_long_segments(gsd_result, original_time_array=original_time_array)
        return gsd_result, v_acc_for_plot

    def _get_csv_output_path(self, file_end, output_title):
        output_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir=self.directory_path,
            initialfile=self.filename + file_end,
            title=output_title
            )
        return output_path
    
    def _get_plot_output_path(self, file_end, output_title):
        output_path=filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf"), ("SVG File", "*.svg")],
            initialdir=self.directory_path,
            initialfile=self.filename + file_end,
            title=output_title
        )
        return output_path