import tkinter as tk
from typing import Callable, Optional

from Main.GUI_Tabs.gui_style import make_action_button, make_radiobutton
import numpy as np
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from OMX_To_CSV import matlab_datenum_to_datetime


class PlotOMX:
    def __init__(
        self,
        data,
        filename,
        parent_widget,
        progress: Optional[Callable[[int], None]] = None,
    ):
        self.data = data
        self.filename = filename
        self.parent = parent_widget
        self.view_change_callbacks = []
        self.highlight_change_callbacks = []

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

        # Precompute all datetime values
        self.raw_datetimes = self._convert_timestamps_chunked(
            self.raw_timestamps, progress_callback=progress
        )

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

        # Pan path reads these before the first wheel zoom; match zoom_to_bounds caches
        self.current_x = np.asarray(x_mpl_nums, dtype=float)
        self.current_y = y_columns
        self.current_view = tuple(float(x) for x in self.ax.get_xlim())

        self.tool_mode = tk.StringVar(value="browse")
        self._region_anchor = None
        self._region_preview = None
        self._highlight_span = None
        self._highlight_range_mpl = None

        toolbar = tk.Frame(self.container)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(0, 2))

        row1 = tk.Frame(toolbar)
        row1.pack(side=tk.TOP, fill=tk.X)

        btn_row = tk.Frame(row1)
        btn_row.pack(side=tk.RIGHT)
        make_action_button(btn_row, text="Clear highlight", command=self._on_clear_highlight_clicked).pack(
            side=tk.RIGHT, padx=(4, 0)
        )
        make_action_button(btn_row, text="⟳ Reset View", command=self._reset_view).pack(
            side=tk.RIGHT, padx=(4, 0)
        )

        left = tk.Frame(row1)
        left.pack(side=tk.LEFT)
        tk.Label(left, text="Plot tool:").pack(side=tk.LEFT, padx=(0, 4))
        make_radiobutton(
            left,
            text="Browse (pan & wheel)",
            variable=self.tool_mode,
            value="browse",
        ).pack(side=tk.LEFT, padx=2)
        make_radiobutton(
            left,
            text="Zoom to rectangle",
            variable=self.tool_mode,
            value="zoom_rect",
        ).pack(side=tk.LEFT, padx=2)
        make_radiobutton(
            left,
            text="Highlight range",
            variable=self.tool_mode,
            value="highlight",
        ).pack(side=tk.LEFT, padx=2)

        self.tool_mode.trace_add("write", self._on_tool_mode_changed)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.container)
        self.canvas.draw()
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=False)

        self._sync_plot_tool_cursor()

        self.pan_start = {"x": None}

        self.fig.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.fig.canvas.mpl_connect("button_press_event", self._on_button_press)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_mouse_drag)
        self.fig.canvas.mpl_connect("button_release_event", self._on_button_release)
        self.fig.canvas.mpl_connect("key_press_event", self._on_key_press)

        self.edge_labels = []
        self._update_edge_labels()
        self.fig.canvas.mpl_connect('draw_event', self._update_edge_labels)
        self.fig.canvas.mpl_connect('button_release_event', self._update_edge_labels)
        self.fig.canvas.mpl_connect('scroll_event', self._update_edge_labels)

    # -------------------------Public Methods---------------------------------
    
    def register_view_change_callback(self, callback):
        self.view_change_callbacks.append(callback)

    def register_highlight_change_callback(self, callback):
        self.highlight_change_callbacks.append(callback)

    def _notify_highlight_changed(self):
        for cb in self.highlight_change_callbacks:
            cb()

    def get_current_bounds(self):
        x_min, x_max = self.ax.get_xlim()
        return mdates.num2date(x_min), mdates.num2date(x_max)

    def get_highlight_range(self):
        """Naive datetimes for the current highlight, or None. For a single export window."""
        if self._highlight_range_mpl is None:
            return None
        lo, hi = self._highlight_range_mpl
        return mdates.num2date(lo), mdates.num2date(hi)

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
        # Must refresh downsampled line data, not only xlim — otherwise after a
        # narrow zoom (e.g. highlight) the lines still cover a tiny x span and
        # the rest of the plot looks blank until another zoom reloads data.
        self.zoom_to_bounds(self.initial_xlim[0], self.initial_xlim[1])
        self._notify_view_change()

    def _get_raw_bounds(self):
        x_min, x_max = self.ax.get_xlim()
        return x_min, x_max

    def _notify_view_change(self):
        for cb in self.view_change_callbacks:
            cb()

    def _on_tool_mode_changed(self, *_args):
        self._cancel_region_interaction()
        self.pan_start["x"] = None
        self._sync_plot_tool_cursor()

    def _sync_plot_tool_cursor(self):
        try:
            if self.tool_mode.get() == "browse":
                self.canvas_widget.configure(cursor="")
            else:
                self.canvas_widget.configure(cursor="crosshair")
        except tk.TclError:
            pass

    def _clear_region_preview(self):
        if self._region_preview is not None:
            self._region_preview.remove()
            self._region_preview = None

    def _cancel_region_interaction(self):
        self._region_anchor = None
        self._clear_region_preview()

    def _clear_highlight(self):
        if self._highlight_span is not None:
            try:
                self._highlight_span.remove()
            except ValueError:
                pass
            self._highlight_span = None
        self._highlight_range_mpl = None
        self.canvas.draw_idle()

    def _on_clear_highlight_clicked(self):
        self._clear_highlight()
        self._notify_highlight_changed()

    def _on_key_press(self, event):
        if event.key != "escape":
            return
        self._cancel_region_interaction()
        self.pan_start["x"] = None
        self.canvas.draw_idle()

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
        if event.button != 1:
            return
        try:
            self.canvas_widget.focus_set()
        except tk.TclError:
            pass

        mode = self.tool_mode.get()
        if mode in ("zoom_rect", "highlight"):
            if event.inaxes != self.ax or event.xdata is None:
                return
            self.pan_start["x"] = None
            self._region_anchor = float(event.xdata)
            self._clear_region_preview()
            return

        self._cancel_region_interaction()
        self.pan_start["x"] = event.xdata

    def _on_mouse_drag(self, event):
        mode = self.tool_mode.get()
        if mode in ("zoom_rect", "highlight") and self._region_anchor is not None:
            if event.xdata is None:
                return
            self._clear_region_preview()
            lo = min(self._region_anchor, float(event.xdata))
            hi = max(self._region_anchor, float(event.xdata))
            color = (0.2, 0.55, 0.95, 0.28) if mode == "zoom_rect" else (0.95, 0.75, 0.1, 0.35)
            self._region_preview = self.ax.axvspan(lo, hi, facecolor=color, edgecolor="none", zorder=10)
            self.canvas.draw_idle()
            return

        if mode != "browse":
            return
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
        if event.button != 1:
            return

        mode = self.tool_mode.get()
        if self._region_anchor is not None and mode in ("zoom_rect", "highlight"):
            anchor = self._region_anchor
            self._region_anchor = None
            self._clear_region_preview()
            x1 = event.xdata
            if x1 is None:
                self.canvas.draw_idle()
                return
            lo = self._snap_to_seconds(min(anchor, float(x1)))
            hi = self._snap_to_seconds(max(anchor, float(x1)))
            if hi - lo <= 1e-12:
                self.canvas.draw_idle()
                return
            if mode == "zoom_rect":
                self.zoom_to_bounds(lo, hi)
                self._notify_view_change()
            else:
                self._clear_highlight()
                span = self.ax.axvspan(
                    lo,
                    hi,
                    facecolor=(0.95, 0.8, 0.15, 0.28),
                    edgecolor=(0.7, 0.55, 0.05, 0.9),
                    linewidth=0.8,
                    zorder=1,
                )
                self._highlight_span = span
                self._highlight_range_mpl = (lo, hi)
                self.canvas.draw_idle()
                self._notify_highlight_changed()
            return

        self.pan_start["x"] = None
        self._notify_view_change()

    def _snap_to_seconds(self, matplotlib_date):
        dt = mdates.num2date(matplotlib_date)
        dt_snapped = dt.replace(microsecond=0)
        return mdates.date2num(dt_snapped)
    
    def _convert_timestamps_chunked(
        self,
        timestamps,
        chunk_size=10000,
        progress_callback: Optional[Callable[[int], None]] = None,
    ):
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
                if progress_callback is not None:
                    progress_callback(current_milestone)

        print("100% done - Timestamp conversion complete!")
        if progress_callback is not None:
            progress_callback(100)
        return np.array(datetimes)