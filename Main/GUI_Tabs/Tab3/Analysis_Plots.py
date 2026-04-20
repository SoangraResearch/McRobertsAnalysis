import numpy as np
import warnings
from tkinter import ttk

from Main.GUI_Tabs.gui_style import apply_notebook_tab_pointer_cursor

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

active_notebook = None

def display_combined_plots(linear_plots, nonlinear_plots, plot_frame):
    global active_notebook

    for widget in plot_frame.winfo_children():
        widget.destroy()

    notebook = ttk.Notebook(plot_frame)
    notebook.pack(fill='both', expand=True)
    apply_notebook_tab_pointer_cursor(notebook)
    active_notebook = notebook

    num_tabs = max(len(linear_plots), len(nonlinear_plots))

    for i in range(num_tabs):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=f"Period {i + 1}")

        plots_frame = ttk.Frame(tab)
        plots_frame.pack(fill='both', expand=True)

        linear_frame = ttk.Frame(plots_frame)
        nonlinear_frame = ttk.Frame(plots_frame)

        # Capture i, linear_frame, nonlinear_frame by value (default args) so each
        # deferred draw targets the correct tab. Without this, all draws would
        # reference the last loop iteration's frames, rendering every plot into one tab.
        def draw(i=i, lf=linear_frame, nf=nonlinear_frame):
            if i < len(linear_plots):
                fig = linear_plots[i]
                fig.set_size_inches(5, 3.5)
                canvas = FigureCanvasTkAgg(fig, master=lf)
                canvas.draw()
                canvas.get_tk_widget().pack(fill='both', expand=True)

            if i < len(nonlinear_plots):
                fig = nonlinear_plots[i]
                fig.set_size_inches(5, 3.5)
                canvas = FigureCanvasTkAgg(fig, master=nf)
                canvas.draw()
                canvas.get_tk_widget().pack(fill='both', expand=True)

            lf.pack(side='left', fill='both', expand=True)
            nf.pack(side='right', fill='both', expand=True)

        # Defer drawing to ensure frames are laid out before embedding canvases
        plot_frame.after(50, draw)

    if num_tabs > 0:
        notebook.select(0)

def linear_plot(
    time_vector,
    acc_ap_pp,
    acc_wave_detrended,
    acc_wave_2,
    hs_times,
    hs_selected_idx,
    to_times,
    to_selected_idx,
    invalid_hs_idx,
    invalid_hs_times,
    plot_frame,
    plot_num,
    embed=True,
):
    global active_notebook

    print("Plotting")

    fig = Figure(figsize=(3.5, 3), dpi=100, constrained_layout=True)
    ax = fig.add_subplot(111)
    ax.tick_params(axis='both', labelsize=14)

    ax.plot(time_vector, acc_ap_pp, 'b--', label='acc_ap')
    ax.plot(time_vector, acc_wave_detrended, color="grey", linestyle="dotted", label='dcwt1')
    ax.plot(time_vector, acc_wave_2, 'k', label='dcwt2')
    ax.plot(hs_times, acc_wave_detrended[hs_selected_idx], linestyle='None', color='red', label='HS', marker="*", markersize=10)
    ax.plot(to_times, acc_wave_2[to_selected_idx], linestyle='None', color='lime', label='TO', marker="*", markersize=10)
    ax.plot(invalid_hs_times, acc_wave_detrended[invalid_hs_idx], linestyle='None', color='orange', label='HS invalid', marker="*", markersize=10)

    ax.set_title("Linear Plot", fontsize=20)
    ax.set_xlabel("Time [s]", fontsize=16)
    ax.legend(loc="upper right")

    if not embed:
        return fig

    if plot_frame is None:
        return fig

    if plot_num == 0 or not hasattr(plot_frame, "notebook"):
        print("removing previous tabs for linear plots")
        for widget in plot_frame.winfo_children():
            widget.destroy()
        plot_frame.notebook = ttk.Notebook(plot_frame)
        plot_frame.notebook.pack(fill='both', expand=True)
        apply_notebook_tab_pointer_cursor(plot_frame.notebook)

    active_notebook = plot_frame.notebook

    tab = ttk.Frame(plot_frame.notebook)
    plot_frame.notebook.add(tab, text=f"Period {plot_num + 1}")

    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

    plot_frame.notebook.select(tab)

    return fig

def nonlinear_plot(
    time,
    AveLnDiv,
    LyES,
    timeS,
    LyESline,
    LyEL,
    timeL,
    LyELline,
    plot_frame,
    plot_num,
    embed=True,
):
    global active_notebook

    print("Plotting nonlinear")

    fig = Figure(figsize=(3.5, 3), dpi=100, constrained_layout=True)
    ax = fig.add_subplot(111)
    ax.tick_params(axis='both', labelsize=14)

    ax.plot(time, AveLnDiv, color="black")
    ax.set_title("LyE", fontsize=20)
    ax.set_xlabel("Time [s]", fontsize=16)
    ax.set_ylabel("<ln(divergence)>", fontsize=16)

    if not np.isnan(LyES):
        ax.plot(timeS, LyESline, color="red", linewidth=3, label="LyE_Short = {}".format(LyES))
    if not np.isnan(LyEL):
        ax.plot(timeL, LyELline, color="green", linewidth=3, label="LyE_Long = {}".format(LyEL))

    ax.legend(loc="best")

    if not embed:
        return fig

    if plot_frame is None:
        return fig

    if plot_num == 0 or not hasattr(plot_frame, "notebook"):
        print("removing previous tabs for nonlinear plots")
        for widget in plot_frame.winfo_children():
            widget.destroy()
        plot_frame.notebook = ttk.Notebook(plot_frame)
        plot_frame.notebook.pack(fill='both', expand=True)
        apply_notebook_tab_pointer_cursor(plot_frame.notebook)

    active_notebook = plot_frame.notebook

    tab = ttk.Frame(plot_frame.notebook)
    plot_frame.notebook.add(tab, text=f"Period {plot_num + 1}")

    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

    plot_frame.notebook.select(tab)

    return fig