import os
import tkinter as tk
from tkinter import filedialog, messagebox

class Tab2Controller:
    def __init__(self, tab_frame):
        self.tab = tab_frame

# -------------------------Public Methods---------------------------------

    def load_file(self, file_path):
        file_path = filedialog.askopenfilename(filetypes=[("CSV/JSON files", "*.csv *.json")])
        if not file_path:
            return
        
        mobiliseD_directory_path = os.path.dirname(file_path)
        mobiliseD_filename = os.path.splitext(os.path.basename(file_path))[0]

        try:
            if file_path.endswith(".csv"):
                messagebox.showinfo("Loaded", f"Loaded file:\n{file_path}")
                mobiliseD_file = file_path
                file_path.set(f"File loaded: {mobiliseD_filename}")
            else:
                raise ValueError("Unsupported file format")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

# -------------------------Private/Helper Methods---------------------------------