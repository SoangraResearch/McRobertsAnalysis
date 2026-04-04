import tkinter as tk

from Main.GUI_Tabs.hover_button import make_hover_button
import numpy as np
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from OMX_To_CSV import matlab_datenum_to_datetime


class PlotOMX:
    def __init__(self, data, filename, parent_widget):
        self.data = data
        self.filename = filename
        self.parent = parent_widget
        self.view_change_callbacks = []

        print("plotting acceleration plot")

        # Clear previous content
        for widget in self.parent.winfo_children():
            widget.destroy()

        # Container for canvas and button
        self.container = tk.Frame(self.parent)
        self.container.pack(fill="both", expand=False)

        # Setup figure and axes
        self.fig = Figure(figsize=(10, 3.5), dpi=100)
        self.ax = self.fig.add_subplot(111)

        # Store raw data
        self.raw_timestamps = self.data['ACC'][:, 0]
        self.raw_y = self.data['ACC'][:, 1:4]

        # Convert all timestamps to datetime for bounds calculation
        all_datetimes = [matlab_datenum_to_datetime(ts) for ts in self.raw_timestamps]

        # Precompute all datetime values
        self.raw_datetimes = self._convert_timestamps_chunked(self.raw_timestamps)

        self.max_points = 5000
        self.n_raw = len(self.raw_datetimes)
        self.global_bin_edges = np.linspace(0, self.n_raw, self.max_points + 1, dtype=int)
        
        # Get downsampled data using full bounds
        x_mpl, y_columns = self._downsample_data(self.raw_datetimes[0], self.raw_datetimes[-1], max_points=self.max_points)

        # Convert x data to matplotlib's numeric date format
        x_mpl_nums = mdates.date2num(x_mpl)

        # Plot data
        self.lines = []
        for i in range(y_columns.shape[1]):
            line, = self.ax.plot_date(x_mpl_nums, y_columns[:, i], '-', label=['Ax', 'Ay', 'Az'][i])
            self.lines.append(line)

        # Remove x-axis labels and ticks
        self.ax.xaxis.set_major_locator(mticker.NullLocator())
        self.ax.xaxis.set_major_formatter(mticker.NullFormatter())

        # Format x-axis dates
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
        self.x_datetime = x_mpl
        self.initial_xlim = [mdates.date2num(x_mpl[0]), mdates.date2num(x_mpl[-1])]
        self.ax.set_xlim(self.initial_xlim)
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
        self.fig.canvas.mpl_connect("button_release_event", self._on_button_release)

        # Initialize edge labels
        self.edge_labels = []
        self._update_edge_labels()
        self.fig.canvas.mpl_connect('draw_event', self._update_edge_labels)
        self.fig.canvas.mpl_connect('button_release_event', self._update_edge_labels)
        self.fig.canvas.mpl_connect('scroll_event', self._update_edge_labels)

        # Reset view button
        reset_button = make_hover_button(self.container, text="⟳ Reset View", command=self._reset_view)
        reset_button.place(x=10, y=10)

    # -------------------------Public Methods---------------------------------
    
    def register_view_change_callback(self, callback):
        self.view_change_callbacks.append(callback)

    def get_current_bounds(self):
        x_min, x_max = self.ax.get_xlim()
        return mdates.num2date(x_min), mdates.num2date(x_max)

    def zoom_to_bounds(self, xmin, xmax):
        xmin, xmax = self._clamp_xlim(xmin, xmax)

        current_xlim = self.ax.get_xlim()
        eps = 1e-12
        if abs(current_xlim[0] - xmin) < eps and abs(current_xlim[1] - xmax) < eps:
            return

        x_dt, y_columns = self._downsample_data(xmin, xmax, max_points=self.max_points)
        xnums = mdates.date2num(x_dt)

        for line, col in zip(self.lines, range(y_columns.shape[1])):
            line.set_data(xnums, y_columns[:, col])

        self.ax.set_xlim(xmin, xmax)
        self.ax.set_ylim(self.y_limits)
        self.canvas.draw_idle()
        self._update_edge_labels()

        self.current_x = xnums
        self.current_y = y_columns
        self.current_view = (xmin, xmax)

    # -------------------------Private/Helper Methods---------------------------------

    def _downsample_data(self, x_min, x_max, max_points=5000):
        if isinstance(x_min, (int, float)):
            x_min = mdates.num2date(x_min)
        if isinstance(x_max, (int, float)):
            x_max = mdates.num2date(x_max)

        if x_min.tzinfo is not None:
            x_min = x_min.replace(tzinfo=None)
        if x_max.tzinfo is not None:
            x_max = x_max.replace(tzinfo=None)

        start_idx = np.searchsorted(self.raw_datetimes, x_min, side="left")
        end_idx = np.searchsorted(self.raw_datetimes, x_max, side="right")

        x_range = self.raw_datetimes[start_idx:end_idx]
        y_range = self.raw_y[start_idx:end_idx, :]

        n_points = len(x_range)
        if n_points <= max_points:
            return x_range, y_range

        bin_edges = np.linspace(0, n_points, max_points + 1, dtype=int)

        x_down = []
        y_down = []
        for i in range(max_points):
            start = bin_edges[i]
            end = bin_edges[i + 1]
            if start >= end:
                continue
            bin_data = y_range[start:end]
            max_idx = np.argmax(np.abs(bin_data[:, 0])) if bin_data.shape[1] > 0 else 0
            x_down.append(x_range[start + max_idx])
            y_down.append(y_range[start + max_idx])
        x_down.append(x_range[-1])
        y_down.append(y_range[-1])

        return np.array(x_down), np.vstack(y_down)
    
    def _reset_view(self):
        self.ax.set_xlim(self.initial_xlim)
        self.ax.set_ylim(self.y_limits)
        self.canvas.draw_idle()
        self._update_edge_labels()
        self._notify_view_change()

    def _get_raw_bounds(self):
        x_min, x_max = self.ax.get_xlim()
        return x_min, x_max

    def _notify_view_change(self):
        for cb in self.view_change_callbacks:
            cb()

    def _update_edge_labels(self, event=None):
        for label in getattr(self, 'edge_labels', []):
            label.remove()
        self.edge_labels = []

        x_min, x_max = self.ax.get_xlim()
        left_label = mdates.num2date(x_min).strftime('%Y-%m-%d %H:%M:%S')
        right_label = mdates.num2date(x_max).strftime('%Y-%m-%d %H:%M:%S')

        self.edge_labels = [self.ax.text(0, -0.08, left_label, transform=self.ax.transAxes, ha='left', va='top', fontsize=8), self.ax.text(1, -0.08, right_label, transform=self.ax.transAxes, ha='right', va='top', fontsize=8)]
        self.canvas.draw_idle()
    
    def _matplotlib_num_to_matlab_datenum(mpl_num):
        return mpl_num + 366

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
        zoom_factor = 0.8 if event.step > 0 else 1.2

        mouse_x = event.xdata
        new_range = range_x * zoom_factor

        new_x_min = mouse_x - (mouse_x - x_min) * zoom_factor
        new_x_max = mouse_x + (x_max - mouse_x) * zoom_factor

        if new_range > (self.initial_xlim[1] - self.initial_xlim[0]):
            new_x_min, new_x_max = self.initial_xlim
        else:
            new_x_min, new_x_max = self._clamp_xlim(new_x_min, new_x_max)

        new_x_min = self._snap_to_seconds(new_x_min)
        new_x_max = self._snap_to_seconds(new_x_max)

        self.zoom_to_bounds(new_x_min, new_x_max)
        
        if hasattr(self, 'scroll_timer'):
            self.container.after_cancel(self.scroll_timer)
        
        self.scroll_timer = self.container.after(100, self._notify_view_change)

    def _on_button_press(self, event):
        if event.button == 1:
            self.pan_start["x"] = event.xdata

    def _on_mouse_drag(self, event):
        if self.pan_start["x"] is None or event.xdata is None:
            return

        dx = self.pan_start["x"] - event.xdata
        x_min, x_max = self.ax.get_xlim()
        new_x_min = x_min + dx
        new_x_max = x_max + dx
        new_x_min, new_x_max = self._clamp_xlim(new_x_min, new_x_max)

        new_x_min = self._snap_to_seconds(new_x_min)
        new_x_max = self._snap_to_seconds(new_x_max)

        old_min, old_max = self.current_view
        eps = 1e-12
        if abs(new_x_min - old_min) < eps and abs(new_x_max - old_max) < eps:
            return

        overlap_min = max(old_min, new_x_min)
        overlap_max = min(old_max, new_x_max)
        overlap_len = max(0.0, overlap_max - overlap_min)
        view_len = new_x_max - new_x_min if (new_x_max - new_x_min) != 0 else 1.0

        if overlap_len / view_len < 0.20:
            self.zoom_to_bounds(new_x_min, new_x_max)
            return

        segments_x = []
        segments_y = []

        if new_x_min < old_min:
            left_min = new_x_min
            left_max = min(old_min, new_x_max)
            lx_dt, ly = self._downsample_data(left_min, left_max, max_points=self.max_points)
            lx = mdates.date2num(lx_dt)
            if lx.size:
                segments_x.append(lx)
                segments_y.append(ly)

        if self.current_x is not None and self.current_y is not None:
            mask = (self.current_x >= overlap_min) & (self.current_x <= overlap_max)
            if np.any(mask):
                segments_x.append(self.current_x[mask])
                segments_y.append(self.current_y[mask])

        if new_x_max > old_max:
            right_min = max(old_max, new_x_min)
            right_max = new_x_max
            rx_dt, ry = self._downsample_data(right_min, right_max, max_points=self.max_points)
            rx = mdates.date2num(rx_dt)
            if rx.size:
                segments_x.append(rx)
                segments_y.append(ry)

        if not segments_x:
            self.zoom_to_bounds(new_x_min, new_x_max)
            return

        all_x = np.concatenate(segments_x)
        all_y = np.vstack(segments_y)

        order = np.argsort(all_x)
        all_x = all_x[order]
        all_y = all_y[order]

        if len(all_x) > 1:
            diffs = np.diff(all_x)
            keep = np.ones(len(all_x), dtype=bool)
            keep[1:] = diffs > 1e-9
            all_x = all_x[keep]
            all_y = all_y[keep]

        # Update caches
        self.current_x = all_x
        self.current_y = all_y
        self.current_view = (new_x_min, new_x_max)

        for i, line in enumerate(self.lines):
            line.set_data(self.current_x, self.current_y[:, i])

        # Move axes and redraw
        self.ax.set_xlim(new_x_min, new_x_max)
        self.canvas.draw_idle()

    def _on_button_release(self, event):
        if event.button == 1:
            self.pan_start["x"] = None
            self._notify_view_change()

    def _snap_to_seconds(self, matplotlib_date):
        dt = mdates.num2date(matplotlib_date)
        dt_snapped = dt.replace(microsecond=0)
        return mdates.date2num(dt_snapped)
    
    def _convert_timestamps_chunked(self, timestamps, chunk_size=10000):
        total_timestamps = len(timestamps)
        datetimes = []
        last_reported_percent = -1
        
        print(f"Converting {total_timestamps:,} timestamps...")
        
        for i in range(0, total_timestamps, chunk_size):
            chunk = timestamps[i:i + chunk_size]
            chunk_datetimes = [
                matlab_datenum_to_datetime(ts).replace(tzinfo=None) 
                for ts in chunk
            ]
            datetimes.extend(chunk_datetimes)
            
            progress_count = min(i + chunk_size, total_timestamps)
            progress_percent = (progress_count / total_timestamps) * 100
            
            current_milestone = int(progress_percent // 10) * 10
            if current_milestone > last_reported_percent and current_milestone > 0:
                print(f"{current_milestone}% done")
                last_reported_percent = current_milestone
        
        print("100% done - Timestamp conversion complete!")
        return np.array(datetimes)