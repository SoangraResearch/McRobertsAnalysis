import os
from tkinter import filedialog, messagebox
from Ayush_Analysis import linear_analysis, nonlinear_analysis
from Ayush_Analysis_Plot import display_combined_plots

class Tab1Controller:
    def __init__(self, tab_frame):
        self.tab = tab_frame

        #files
        self.file = None
        self.directory_path = None
        self.filename = None

        #self.plot_frame = None

# -------------------------Public Methods---------------------------------

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV/JSON files", "*.csv *.json")])
        if not file_path:
            return
        
        self.set_file(file_path)

        try:
            if file_path.endswith(".csv"):
                messagebox.showinfo("Loaded", f"Loaded file:\n{file_path}")

                file_path = (f"File loaded: {self.filename}")
                return file_path
            
                # linear_df = None
                # linear_plots = None
                # nonlinear_df = None
                # nonlinear_plots = []

            else:
                raise ValueError("Unsupported file format")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))
            return "None"

    def set_file(self, file_path):
        self.file = file_path
        self.directory_path = os.path.dirname(file_path)
        self.filename = os.path.splitext(os.path.basename(file_path))[0]

    def analyze_data(self, plot_frame, assume_walking):
        linear_df, linear_plots = linear_analysis(self.file, plot_frame, assume_walking)
        nonlinear_df, nonlinear_plots = nonlinear_analysis(self.file, plot_frame, assume_walking)
        display_combined_plots(linear_plots, nonlinear_plots, plot_frame)
        load_save_plot_buttons()

# -------------------------Private/Helper Methods---------------------------------
