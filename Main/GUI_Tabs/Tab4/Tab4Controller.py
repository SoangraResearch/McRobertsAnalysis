from tkinter import filedialog, messagebox
from Main.GUI_Tabs.gui_style import restore_main_window_focus
import os

class Tab4Controller:
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
        self.analysis_df = None
        self.plots = None

    # -------------------------Public Methods---------------------------------
    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV/JSON files", "*.csv *.json")])
        restore_main_window_focus(self.tab)
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

    # -------------------------Private/Helper Methods---------------------------------

    def _reset_tab(self):
        self.analysis_df = None
        self.plots = None

        if self.plot_frame != None:
            for widget in self.plot_frame.winfo_children():
                widget.destroy()