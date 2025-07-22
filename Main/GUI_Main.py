import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

#setting directory properly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# -------------------------Tkinter Setup---------------------------------

# Create the main window
root = tk.Tk()
root.title("McRoberts Analysis")
root.geometry("1000x600")

tab_control = ttk.Notebook(root)
tab1 = tk.Frame(tab_control)
tab_control.add(tab1, text="Select Data") #First Tab

tab_control.pack(expand=1, fill='both')

# Global variables
# selected_file = None
# extracted_df = None
start_time_var = tk.StringVar()
stop_time_var = tk.StringVar()
file_start_time_var = tk.StringVar()
file_stop_time_var = tk.StringVar()
label_var = tk.StringVar()
export_format_var = tk.StringVar()

# -------------------------Tab 1 Select Data---------------------------------
#Loading file
def load_file():
    global selected_file #, extracted_df
    file_path = filedialog.askopenfilename(filetypes=[("OMX file", "*.OMX")])
    if not file_path:
        return
    
    ##WIP

load_button1 = tk.Button(tab1, text="Load OMX File", command=load_file)
load_button1.pack(pady=10)
    


# -------------------------Running the GUI---------------------------------
root.mainloop()