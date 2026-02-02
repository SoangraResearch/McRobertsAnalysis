import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from Ayush_Analysis import linear_analysis, nonlinear_analysis
from Ayush_Analysis_Plot import display_combined_plots, get_current_selected_plot

class Tab1Controller:
    def __init__(self, tab_frame):
        self.tab = tab_frame

        #files
        self.file = None
        self.directory_path = None
        self.filename = None
        self.export_folder = None

        #data
        self.linear_df = None
        self.linear_plots = None
        self.nonlinear_df = None
        self.onlinear_plots = None

        #self.plot_frame = None

# -------------------------Public Methods---------------------------------

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV/JSON files", "*.csv *.json")])
        if not file_path:
            return
        
        self._set_file(file_path)

        try:
            if file_path.endswith(".csv"):
                messagebox.showinfo("Loaded", f"Loaded file:\n{file_path}")

                file_path = (f"File loaded: {self.filename}")
                return file_path
            
                # nonlinear_plots = []

            else:
                raise ValueError("Unsupported file format")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))
            return "None"
        
        #TODO: reset plots and data

    def do_linear_analysis(self, plot_frame, assume_walking):
        self.linear_df, self.linear_plots = linear_analysis(self.file, plot_frame, assume_walking.get())
        self._load_save_plot_buttons(plot_frame)
        messagebox.showinfo("Linear Analysis", f"Linear analysis complete")

        if(self.nonlinear_plots != None):
            display_combined_plots(self.linear_plots, self.nonlinear_plots, self.plot_frame)

    def do_nonlinear_analysis(self, plot_frame, assume_walking):
        self.nonlinear_df, self.nonlinear_plots = nonlinear_analysis(self.file, plot_frame, assume_walking.get())
        print("nonlinear plots in main gui: " + str(len(self.nonlinear_plots)))
        self._load_save_plot_buttons(plot_frame)
        messagebox.showinfo("Noninear Analysis", f"Nonlinear analysis complete")

        if(self.linear_plots != None):
            print("About to call display_combined_plots() from do_nonlinear_analysis()")
            print(self.linear_plots)
            print(f"linear_plots: {len(self.linear_plots) if self.linear_plots else 0}")
            print(f"nonlinear_plots: {len(self.nonlinear_plots) if self.nonlinear_plots else 0}")

            #delay for nonlinear plot to load properly
            plot_frame.after(100, lambda: display_combined_plots(self.linear_plots, self.nonlinear_plots, plot_frame))

    def analyze_data(self, plot_frame, assume_walking):
        self.linear_df, self.linear_plots = linear_analysis(self.file, plot_frame, assume_walking)
        self.nonlinear_df, self.nonlinear_plots = nonlinear_analysis(self.file, plot_frame, assume_walking)
        display_combined_plots(self.linear_plots, self.nonlinear_plots, plot_frame)
        self._load_save_plot_buttons(plot_frame)

    def save_current_linear_analysis_plot(self, open_prompt_window, plotnum):
        self._create_export_folder()
        try:
            if self.linear_plots is None:
                messagebox.showerror("Error", "No linear analysis plot to save.")
                return
            
            if open_prompt_window:
                output_path = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf"), ("SVG File", "*.svg")],
                    initialdir=self.export_folder,
                    initialfile=self._shorten_filename(self.filename) + "_linear_analysis_plot_" + str(plotnum + 1),
                    title="Save linear analysis plot"
                )
                if not output_path:
                    return False
            else:
                output_path = os.path.join(
                    self.export_folder,
                    self._shorten_filename(self.filename) + "_linear_analysis_plot_" + str(plotnum + 1) + ".png"
                )
            
            print("Full save path length:", len(output_path))
            print("Full save path:", output_path)
            
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
                output_path = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf"), ("SVG File", "*.svg")],
                    initialdir=self.export_folder,
                    initialfile=self._shorten_filename(self.filename) + "_nonlinear_analysis_plot_" + str(plotnum + 1),
                    title="Save nonlinear analysis plot"
                )
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
                output_path=filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv")],
                    initialdir=self.export_folder,
                    initialfile=self._shorten_filename(self.filename) + "_linear_analysis",
                    title="Save linear analysis"
                )
                if not output_path:
                    return False
            else:
                output_path = os.path.join(self.export_folder, self._shorten_filename(self.filename) + "_linear_analysis.csv")
            self.linear_df.to_csv(output_path, index=False)
            messagebox.showinfo("Saved", f"linear analysis saved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_nonlinear_analysis(self, open_prompt_window):
        self.create_export_folder()
        try:
            if self.nonlinear_df is None:
                messagebox.showerror("Error", "No nonlinear analysis to save.")
                return
            if open_prompt_window:
                output_path=filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv")],
                    initialdir=self.export_folder,
                    initialfile=self._shorten_filename(self.filename) + "_nonlinear_analysis",
                    title="Save nonlinear analysis"
                )
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

    def _set_file(self, file_path):
        self.file = file_path
        self.directory_path = os.path.dirname(file_path)
        self.filename = os.path.splitext(os.path.basename(file_path))[0]
    
    def _create_export_folder(self):
        export_folder = self.directory_path
        os.makedirs(export_folder, exist_ok=True)

    def _shorten_filename(self, filename):
        filename = re.sub(r'_from_\d{4}-\d{2}-\d{2}_[0-9\-]+_to_\d{4}-\d{2}-\d{2}_[0-9\-]+', '', filename)
        return filename

    def _load_save_plot_buttons(self, plot_frame):
        save_current_linear_plot = tk.Button(plot_frame, text="Save Linear Plot", command=lambda: self.save_current_linear_analysis_plot(True, get_current_selected_plot(plot_frame)), font=("Arial", 8), relief="raised", bd=2)
        save_current_linear_plot.place(x=15, y=-35, anchor="sw", relx=0, rely=1)
        
        save_current_nonlinear_plot = tk.Button(plot_frame, text="Save Nonlinear Plot", command=lambda: self.save_current_nonlinear_analysis_plot(True, get_current_selected_plot(plot_frame)), font=("Arial", 8), relief="raised", bd=2)
        save_current_nonlinear_plot.place(x=-15, y=-35, anchor="se", relx=1, rely=1)