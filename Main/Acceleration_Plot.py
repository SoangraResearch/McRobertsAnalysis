import tkinter as tk
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class PlotOMX:
    def __init__(self, data, filename, parent_widget):
        self.data = data
        self.filename = filename
        self.parent = parent_widget

        # Clear previous content
        for widget in self.parent.winfo_children():
            widget.destroy()

        # Container for canvas and button
        self.container = tk.Frame(self.parent)
        self.container.pack(fill="both", expand=False)

        # Setup figure and axes
        self.fig = Figure(figsize=(10, 3.5), dpi=100)
        self.ax = self.fig.add_subplot(111)

        # Convert Unix timestamps to Matplotlib dates
        x_unix = self.data['ACC'][:, 0]
        x_mpl = mdates.epoch2num(x_unix)  # ✅ Correct conversion
        y_columns = self.data['ACC'][:, 1:4]

        # Plot data
        self.lines = self.ax.plot(x_mpl, y_columns)

        # Format x-axis ticks as datetime strings
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
        self.fig.autofmt_xdate()

        # Labeling and layout
        self.ax.legend(self.lines, ['Ax', 'Ay', 'Az'], loc='center left', bbox_to_anchor=(1, 0.5))
        self.fig.subplots_adjust(right=0.8)
        self.ax.set_title(f'Plot of {self.filename} Acceleration')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Value')

        self.fig.tight_layout()

        # Store initial x/y limits
        self.x_datetime = x_mpl  # Use the correct format here
        self.initial_xlim = [x_mpl[0], x_mpl[-1]]
        self.y_limits = self.ax.get_ylim()

        # Embed canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.container)
        self.canvas.draw()
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=False)

        # Pan tracking
        self.pan_start = {"x": None}

        # Bind events
        self.fig.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.fig.canvas.mpl_connect("button_press_event", self._on_button_press)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_mouse_drag)

        # Reset view button
        reset_button = tk.Button(self.container, text="⟳ Reset View", command=self.reset_view)
        reset_button.place(x=10, y=10)

    def reset_view(self):
        self.ax.set_xlim(self.initial_xlim)
        self.ax.set_ylim(self.y_limits)
        self.canvas.draw_idle()

    def zoom_to_bounds(self, xmin, xmax):
        xmin, xmax = self._clamp_xlim(xmin, xmax)
        self.ax.set_xlim(xmin, xmax)
        self.ax.set_ylim(self.y_limits)
        self.canvas.draw_idle()

    def _clamp_xlim(self, new_min, new_max):
        range_width = new_max - new_min
        if new_min < self.initial_xlim[0]:
            new_min = self.initial_xlim[0]
            new_max = new_min + range_width
        if new_max > self.initial_xlim[1]:
            new_max = self.initial_xlim[1]
            new_min = new_max - range_width
        return new_min, new_max

    def _on_scroll(self, event):
        if event.xdata is None:
            return 

        x_min, x_max = self.ax.get_xlim()
        range_x = x_max - x_min
        zoom_factor = 0.7 if event.step > 0 else 1.3

        mouse_x = event.xdata
        new_range = range_x * zoom_factor

        new_x_min = mouse_x - (mouse_x - x_min) * zoom_factor
        new_x_max = mouse_x + (x_max - mouse_x) * zoom_factor

        if new_range > (self.initial_xlim[1] - self.initial_xlim[0]):
            new_x_min, new_x_max = self.initial_xlim
        else:
            new_x_min, new_x_max = self._clamp_xlim(new_x_min, new_x_max)

        self.ax.set_xlim(new_x_min, new_x_max)
        self.ax.set_ylim(self.y_limits)
        self.canvas.draw_idle()

    def _on_button_press(self, event):
        if event.button == 1:
            self.pan_start["x"] = event.xdata

    def _on_mouse_drag(self, event):
        if event.button == 1 and event.xdata is not None and self.pan_start["x"] is not None:
            dx = self.pan_start["x"] - event.xdata
            x_min, x_max = self.ax.get_xlim()
            new_x_min = x_min + dx
            new_x_max = x_max + dx
            new_x_min, new_x_max = self._clamp_xlim(new_x_min, new_x_max)

            self.ax.set_xlim(new_x_min, new_x_max)
            self.ax.set_ylim(self.y_limits)
            self.canvas.draw_idle()
