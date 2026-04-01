import os
import re
import sys
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox
from Main.GUI_Tabs.Tab3.Analysis_code import linear_analysis, nonlinear_analysis
from Main.GUI_Tabs.Tab3.Analysis_Plots import (
    display_combined_plots,
    get_current_selected_plot,
    nonlinear_plot,
)

class Tab3Controller:
    def __init__(self, tab_frame, heavy_job=None):
        self.tab = tab_frame
        self.heavy_job = heavy_job

        #plot frame
        self.plot_frame = None

        #files
        self.file = None
        self.directory_path = None
        self.filename = None
        self.export_folder = None

        #data
        self.linear_df = None
        self.linear_plots = None
        self.nonlinear_df = None
        self.nonlinear_plots = None

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
        self._reset_tab()

    def do_linear_analysis(self, plot_frame, assume_walking):
        """Linear analysis on the main thread (fast); no HeavyJobRunner / indeterminate bar."""
        if self.file is None:
            messagebox.showerror("Error", "No file loaded.")
            return

        for widget in plot_frame.winfo_children():
            widget.destroy()

        try:
            self.linear_df, self.linear_plots = linear_analysis(
                self.file,
                plot_frame,
                assume_walking.get(),
                build_plots=True,
            )
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Linear Analysis Error", str(e))
            return

        self._load_save_plot_buttons(plot_frame)
        messagebox.showinfo("Linear Analysis", "Linear analysis complete")
        if self.nonlinear_plots is not None:
            display_combined_plots(self.linear_plots, self.nonlinear_plots, plot_frame)
        self.plot_frame = plot_frame

    def do_nonlinear_analysis(self, plot_frame, assume_walking):
        """Run nonlinear analysis on a background thread; status in the bottom bar."""
        if self.file is None:
            messagebox.showerror("Error", "No file loaded.")
            return

        for widget in plot_frame.winfo_children():
            widget.destroy()

        def update_progress(text):
            if self.heavy_job:
                self.heavy_job.schedule_status_message(f"Nonlinear: {text}")

        def worker():
            return nonlinear_analysis(
                self.file,
                assume_walking.get(),
                progress_callback=update_progress if self.heavy_job else None,
            )

        def on_success(result):
            df, plot_data_list = result
            self._on_nonlinear_complete(plot_frame, df, plot_data_list)

        def on_error(msg):
            messagebox.showerror("Analysis Error", msg)

        if self.heavy_job:
            if not self.heavy_job.run(
                "Nonlinear analysis…",
                worker,
                on_success=on_success,
                on_error=on_error,
            ):
                return
        else:
            try:
                result = worker()
                on_success(result)
            except Exception:
                traceback.print_exc()
                on_error(str(sys.exc_info()[1]))

    def _on_nonlinear_complete(self, plot_frame, df, plot_data_list):
        """Called on main thread after analysis finishes.

        Converts raw plot data dicts into Matplotlib figures here because
        Tkinter widgets can only be created on the main thread.
        """
        self.nonlinear_df = df

        # Build Matplotlib figures from the raw data collected in nonlinear_analysis()
        self.nonlinear_plots = []
        for i, pd in enumerate(plot_data_list):
            fig = nonlinear_plot(
                pd['time'], pd['AveLnDiv'], pd['LyES'], pd['timeS'], pd['lyESline'],
                pd['LyEL'], pd['timeL'], pd['LyELline'], plot_frame, i
            )
            self.nonlinear_plots.append(fig)

        print("nonlinear plots in main gui: " + str(len(self.nonlinear_plots)))
        self._load_save_plot_buttons(plot_frame)
        messagebox.showinfo("Nonlinear Analysis", "Nonlinear analysis complete")

        # If linear analysis was run earlier, show both side by side
        if self.linear_plots:
            plot_frame.after(100, lambda: display_combined_plots(self.linear_plots, self.nonlinear_plots, plot_frame))
        self.plot_frame = plot_frame

    def analyze_data(self, plot_frame, assume_walking):
        self.linear_df, self.linear_plots = linear_analysis(self.file, plot_frame, assume_walking)
        self.nonlinear_df, plot_data_list = nonlinear_analysis(self.file, assume_walking)
        # Build figures from raw data on the main thread
        self.nonlinear_plots = []
        for i, pd in enumerate(plot_data_list):
            fig = nonlinear_plot(
                pd['time'], pd['AveLnDiv'], pd['LyES'], pd['timeS'], pd['lyESline'],
                pd['LyEL'], pd['timeL'], pd['LyELline'], plot_frame, i
            )
            self.nonlinear_plots.append(fig)
        display_combined_plots(self.linear_plots, self.nonlinear_plots, plot_frame)
        self._load_save_plot_buttons(plot_frame)
        self.plot_frame = plot_frame

    def save_current_linear_analysis_plot(self, open_prompt_window, plotnum):
        self._create_export_folder()
        try:
            if self.linear_plots is None:
                messagebox.showerror("Error", "No linear analysis plot to save.")
                return
            if open_prompt_window:
                output_path = self._get_plot_output_path("_linear_analysis_plot_", "Save linear analysis plot")
            else:
                output_path = os.path.join(
                    self.export_folder,
                    self._shorten_filename(self.filename) + "_linear_analysis_plot_" + str(plotnum + 1) + ".png"
                )        
            self.linear_plots[plotnum].savefig(output_path, dpi=300)
            messagebox.showinfo("Saved", f"linear analysis plot saved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_current_nonlinear_analysis_plot(self, open_prompt_window, plotnum):
        self._create_export_folder()
        try:
            if self.nonlinear_plots is None:
                messagebox.showerror("Error", "No nonlinear analysis plot to save.")
                return
            if open_prompt_window:
                output_path = self._get_plot_output_path("_nonlinear_analysis_plot_", "Save nonlinear analysis plot")
                if not output_path:
                    return False
            else:
                output_path = os.path.join(
                    self.export_folder,
                    self._shorten_filename(self.filename) + "_nonlinear_analysis_plot_" + str(plotnum + 1) + ".png"
                )
            self.nonlinear_plots[plotnum].savefig(output_path, dpi=300)
            messagebox.showinfo("Saved", f"nonlinear analysis plot saved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_linear_analysis(self, open_prompt_window):
        self._create_export_folder()
        try:
            if self.linear_df is None:
                messagebox.showerror("Error", "No linear analysis to save.")
                return
            if open_prompt_window:
                output_path = self._get_csv_output_path("_linear_analysis", "Save Linear Analysis")
                if not output_path:
                    return False
            else:
                output_path = os.path.join(self.export_folder, self._shorten_filename(self.filename) + "_linear_analysis.csv")
            self.linear_df.to_csv(output_path, index=False)
            messagebox.showinfo("Saved", f"linear analysis saved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_nonlinear_analysis(self, open_prompt_window):
        self._create_export_folder()
        try:
            if self.nonlinear_df is None:
                messagebox.showerror("Error", "No nonlinear analysis to save.")
                return
            if open_prompt_window:
                output_path = self._get_csv_output_path("_nonlinear_analysis", "Save Nonlinear Analysis")
                if not output_path:
                    return False
            else:
                output_path = os.path.join(self.export_folder, self._shorten_filename(self.filename) + "_nonlinear_analysis.csv")
            self.nonlinear_df.to_csv(output_path, index=False)
            messagebox.showinfo("Saved", f"nonlinear analysis saved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_all_linear_analysis_plots(self, open_prompt_window):
        try:
            for i in range(len(self.linear_plots)):
                self.save_current_linear_analysis_plot(open_prompt_window, i)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))  

    def save_all_nonlinear_analysis_plots(self, open_prompt_window):
        try:
            for i in range(len(self.nonlinear_plots)):
                self.save_current_nonlinear_analysis_plot(open_prompt_window, i)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_all_output(self):
        try:
            self.save_linear_analysis(False)
            self.save_nonlinear_analysis(False)
            self.save_all_linear_analysis_plots(False)
            self.save_all_nonlinear_analysis_plots(False)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

# -------------------------Private/Helper Methods---------------------------------
    
    def _reset_tab(self):
        self.linear_df = None
        self.linear_plots = None
        self.nonlinear_df = None
        self.nonlinear_plots = None

        if self.plot_frame != None:
            for widget in self.plot_frame.winfo_children():
                widget.destroy()

    def _create_export_folder(self):
        self.export_folder = self.directory_path
        os.makedirs(self.export_folder, exist_ok=True)

    def _shorten_filename(self, filename):
        filename = re.sub(r'_from_\d{4}-\d{2}-\d{2}_[0-9\-]+_to_\d{4}-\d{2}-\d{2}_[0-9\-]+', '', filename)
        return filename

    def _load_save_plot_buttons(self, plot_frame):
        save_current_linear_plot = tk.Button(plot_frame, text="Save Linear Plot", command=lambda: self.save_current_linear_analysis_plot(True, get_current_selected_plot(plot_frame)), font=("Arial", 8), relief="raised", bd=2)
        save_current_linear_plot.place(x=15, y=-35, anchor="sw", relx=0, rely=1)
        
        save_current_nonlinear_plot = tk.Button(plot_frame, text="Save Nonlinear Plot", command=lambda: self.save_current_nonlinear_analysis_plot(True, get_current_selected_plot(plot_frame)), font=("Arial", 8), relief="raised", bd=2)
        save_current_nonlinear_plot.place(x=-15, y=-35, anchor="se", relx=1, rely=1)

    def _get_plot_output_path(self, file_end, output_title):
        output_path=filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf"), ("SVG File", "*.svg")],
            initialdir=self.directory_path,
            initialfile=self._shorten_filename(self.filename) + file_end,
            title=output_title
        )
        return output_path
    
    def _get_csv_output_path(self, file_end, output_title):
        output_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir=self.directory_path,
            initialfile=self._shorten_filename(self.filename) + file_end,
            title=output_title
            )
        return output_path