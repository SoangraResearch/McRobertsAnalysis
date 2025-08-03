import numpy as np
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def display_combined_plots(linear_plots, nonlinear_plots, plot_frame):
    print("Displaying combined plots")
    
    # Clear any existing widgets
    for widget in plot_frame.winfo_children():
        widget.destroy()
    
    # Create the notebook
    notebook = ttk.Notebook(plot_frame)
    notebook.pack(fill='both', expand=True)
    
    # Determine the number of tabs needed (max of both plot types)
    num_tabs = max(len(linear_plots), len(nonlinear_plots))
    
    for i in range(num_tabs):
        # Create a new tab
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=f"Plot Set {i + 1}")
        
        # Create a frame for side-by-side plots
        plots_frame = ttk.Frame(tab)
        plots_frame.pack(fill='both', expand=True)
        
        # Left side - Linear plot
        if i < len(linear_plots):
            linear_frame = ttk.Frame(plots_frame)
            linear_frame.pack(side='left', fill='both', expand=True)
            
            # Embed the existing linear figure
            canvas_linear = FigureCanvasTkAgg(linear_plots[i], master=linear_frame)
            canvas_linear.draw()
            canvas_linear.get_tk_widget().pack(fill='both', expand=True)
        
        # Right side - Nonlinear plot  
        if i < len(nonlinear_plots):
            nonlinear_frame = ttk.Frame(plots_frame)
            nonlinear_frame.pack(side='right', fill='both', expand=True)
            
            # Embed the existing nonlinear figure
            canvas_nonlinear = FigureCanvasTkAgg(nonlinear_plots[i], master=nonlinear_frame)
            canvas_nonlinear.draw()
            canvas_nonlinear.get_tk_widget().pack(fill='both', expand=True)
    
    # Auto-select the first tab
    if num_tabs > 0:
        notebook.select(0)

def linear_plot(time_vector, acc_ap_pp, acc_wave_detrended, acc_wave_2, hs_times, hs_selected_idx, to_times, to_selected_idx, invalid_hs_idx, invalid_hs_times, plot_frame, plot_num):
    print("Plotting")

    # If plot_num is 0, reset the notebook (remove previous tabs)
    if plot_num == 0 or not hasattr(plot_frame, "notebook"):
        for widget in plot_frame.winfo_children():
            widget.destroy()
        plot_frame.notebook = ttk.Notebook(plot_frame)
        plot_frame.notebook.pack(fill='both', expand=True)

    # Create a new tab for this plot
    tab = ttk.Frame(plot_frame.notebook)
    plot_frame.notebook.add(tab, text=f"Plot {plot_num + 1}")

    # Create a matplotlib figure
    fig = Figure(figsize=(3.5, 3), dpi=100, constrained_layout=True)
    ax = fig.add_subplot(111)
    ax.tick_params(axis='both', labelsize=14)

    # Plot data on the figure
    ax.plot(time_vector, acc_ap_pp, 'b--', label='acc_ap')
    ax.plot(time_vector, acc_wave_detrended, color="grey", linestyle="dotted", label='dcwt1')
    ax.plot(time_vector, acc_wave_2, 'k', label='dcwt2')
    ax.plot(hs_times, acc_wave_detrended[hs_selected_idx], linestyle='None', color='red', label='HS', marker="*", markersize=10)
    ax.plot(to_times, acc_wave_2[to_selected_idx], linestyle='None', color='lime', label='TO', marker="*", markersize=10)
    ax.plot(invalid_hs_times, acc_wave_detrended[invalid_hs_idx], linestyle='None', color='orange', label='HS invalid', marker="*", markersize=10)

    ax.set_title("Linear Plot", fontsize=20)
    ax.set_xlabel('Time [s]', fontsize=16)
    ax.legend(loc="upper right")

    # Embed the figure into the new tab
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

    # Auto-select the newly added tab
    plot_frame.notebook.select(tab)

    return fig

def nonlinear_plot(time, AveLnDiv, LyES, timeS, LyESline, LyEL, timeL, LyELline, plot_frame, plot_num):
    print("Plotting nonlinear")
    
    # If plot_num is 0, reset the notebook (remove previous tabs)
    if plot_num == 0 or not hasattr(plot_frame, "notebook"):
        for widget in plot_frame.winfo_children():
            widget.destroy()
        plot_frame.notebook = ttk.Notebook(plot_frame)
        plot_frame.notebook.pack(fill='both', expand=True)
    
    # Create a new tab for this plot
    tab = ttk.Frame(plot_frame.notebook)
    plot_frame.notebook.add(tab, text=f"LyE Plot {plot_num + 1}")
    
    # Create a matplotlib figure
    fig = Figure(figsize=(3.5, 3), dpi=100, constrained_layout=True)
    ax = fig.add_subplot(111)
    ax.tick_params(axis='both', labelsize=14)
    
    # Plot data on the figure
    ax.plot(time, AveLnDiv, color="black")
    ax.set_title("LyE", fontsize=20)
    ax.set_xlabel("Periods (s)", fontsize=16)
    ax.set_ylabel("<ln(divergence)>", fontsize=16)
    
    # Plot LyE lines if they exist (not NaN)
    if not np.isnan(LyES):
        ax.plot(timeS, LyESline, color="red", linewidth=3, label="LyE_Short = {}".format(LyES))
    if not np.isnan(LyEL):
        ax.plot(timeL, LyELline, color="green", linewidth=3, label="LyE_Long = {}".format(LyEL))
    
    ax.legend(loc="best")
    
    # Embed the figure into the new tab
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)
    
    # Auto-select the newly added tab
    plot_frame.notebook.select(tab)
    
    return fig