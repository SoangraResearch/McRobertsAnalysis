from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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