"""Settings / configuration tab."""

from __future__ import annotations

import copy
import tkinter as tk
from tkinter import ttk
from typing import Dict

from Main import app_config


class Tab5Controller:
    """Walking-detection and (later) nonlinear analysis parameters."""

    _WAVELET_CHOICES = ("gaus1", "gaus2", "db2")

    def __init__(self, tab_frame):
        self.tab = tab_frame
        self._walking_vars: Dict[str, tk.StringVar] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        # Use classic tk frames like Tabs 1–4 so the page matches the system/window
        # background. ttk.Frame/LabelFrame use the clam theme gray and look like the tab strip.
        outer = tk.Frame(self.tab)
        outer.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        walk = tk.LabelFrame(outer, text="Walking detection", padx=10, pady=10)
        walk.pack(fill=tk.X, pady=(0, 8))

        curr_walk = copy.deepcopy(app_config.current["walking"])

        row = 0

        def add_entry(label: str, key: str) -> None:
            nonlocal row
            tk.Label(walk, text=label).grid(
                row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            var = tk.StringVar(value=str(curr_walk[key]))
            self._walking_vars[key] = var
            tk.Entry(walk, textvariable=var, width=16).grid(
                row=row, column=1, sticky=tk.W, pady=4
            )
            row += 1

        add_entry("Min amplitude (g)", "min_amp")
        add_entry("Min walking duration (s)", "min_duration_s")
        add_entry("Peak difference (×0.05 Hz)", "delta")
        add_entry("Alpha (spectral ratio)", "alpha")
        add_entry("Beta (spectral ratio)", "beta")
        add_entry("Step frequency low (Hz)", "step_freq_low")
        add_entry("Step frequency high (Hz)", "step_freq_high")

        def add_combobox(label: str, key: str) -> None:
            nonlocal row
            tk.Label(walk, text=label).grid(
                row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            val = str(curr_walk[key])
            var = tk.StringVar(value=val)
            self._walking_vars[key] = var
            combo_values = list(self._WAVELET_CHOICES)
            if val not in combo_values:
                combo_values = [val] + combo_values
            cb = ttk.Combobox(
                walk,
                textvariable=var,
                values=combo_values,
                state="readonly",
                width=12,
            )
            cb.grid(row=row, column=1, sticky=tk.W, pady=4)
            row += 1

        add_combobox("Wavelet (straight walking)", "wavelet_type_straight")
        add_combobox("Wavelet (turning)", "wavelet_type_turning")

        walk.columnconfigure(1, weight=1)
