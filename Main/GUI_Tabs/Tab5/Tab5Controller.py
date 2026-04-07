"""Settings / configuration tab."""

from __future__ import annotations

import copy
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List

from Main import app_config


class Tab5Controller:
    """Walking-detection and nonlinear analysis parameters."""

    _WAVELET_CHOICES = ("gaus1", "gaus2", "db2")
    _RQA_NORM_CHOICES = ("NON", "EUC", "MIN", "MAX")
    _RQA_SETPARA_CHOICES = ("radius", "recurrence")

    def __init__(self, tab_frame):
        self.tab = tab_frame
        self._walking_vars: Dict[str, tk.StringVar] = {}
        self._phase_space_vars: Dict[str, tk.StringVar] = {}
        self._entropy_vars: Dict[str, tk.StringVar] = {}
        self._lyapunov_vars: Dict[str, tk.StringVar] = {}
        self._rqa_vars: Dict[str, tk.StringVar] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        # Classic tk frames match Tabs 1–4 (system background, not clam ttk gray).
        outer = tk.Frame(self.tab)
        outer.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self._build_walking_section(outer)
        self._build_phase_space_section(outer)
        self._build_entropy_section(outer)
        self._build_lyapunov_section(outer)
        self._build_rqa_section(outer)

    def _build_walking_section(self, outer: tk.Frame) -> None:
        walk = tk.LabelFrame(outer, text="Walking detection", padx=10, pady=10)
        walk.pack(fill=tk.X, pady=(0, 8))
        curr = copy.deepcopy(app_config.current["walking"])
        row = 0

        def add_entry(label: str, key: str) -> None:
            nonlocal row
            tk.Label(walk, text=label).grid(
                row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            var = tk.StringVar(value=str(curr[key]))
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

        def add_wavelet_combo(label: str, key: str) -> None:
            nonlocal row
            tk.Label(walk, text=label).grid(
                row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            val = str(curr[key])
            var = tk.StringVar(value=val)
            self._walking_vars[key] = var
            combo_values = list(self._WAVELET_CHOICES)
            if val not in combo_values:
                combo_values = [val] + combo_values
            ttk.Combobox(
                walk,
                textvariable=var,
                values=combo_values,
                state="readonly",
                width=12,
            ).grid(row=row, column=1, sticky=tk.W, pady=4)
            row += 1

        add_wavelet_combo("Wavelet (straight walking)", "wavelet_type_straight")
        add_wavelet_combo("Wavelet (turning)", "wavelet_type_turning")
        walk.columnconfigure(1, weight=1)

    def _build_phase_space_section(self, outer: tk.Frame) -> None:
        lf = tk.LabelFrame(outer, text="Phase-space reconstruction", padx=10, pady=10)
        lf.pack(fill=tk.X, pady=(0, 8))
        curr = copy.deepcopy(app_config.current["phase_space"])
        row = 0

        def add_entry(label: str, key: str) -> None:
            nonlocal row
            tk.Label(lf, text=label).grid(
                row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            var = tk.StringVar(value=str(curr[key]))
            self._phase_space_vars[key] = var
            tk.Entry(lf, textvariable=var, width=16).grid(
                row=row, column=1, sticky=tk.W, pady=4
            )
            row += 1

        add_entry("AMI max lag", "ami_max_lag")
        add_entry("FNN max embedding dimension", "fnn_max_dim")
        add_entry("FNN Rtol", "fnn_rtol")
        add_entry("FNN Atol", "fnn_atol")
        add_entry("FNN speed", "fnn_speed")
        lf.columnconfigure(1, weight=1)

    def _build_entropy_section(self, outer: tk.Frame) -> None:
        lf = tk.LabelFrame(outer, text="Entropy & multiscale", padx=10, pady=10)
        lf.pack(fill=tk.X, pady=(0, 8))
        curr = copy.deepcopy(app_config.current["entropy"])
        row = 0

        def add_entry(label: str, key: str) -> None:
            nonlocal row
            tk.Label(lf, text=label).grid(
                row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            var = tk.StringVar(value=str(curr[key]))
            self._entropy_vars[key] = var
            tk.Entry(lf, textvariable=var, width=16).grid(
                row=row, column=1, sticky=tk.W, pady=4
            )
            row += 1

        add_entry("Embedding order m (SampEn / PermEn / MSE)", "m")
        add_entry("Tolerance r (ApEn / SampEn / MSE)", "r")
        add_entry("Symbolic entropy L (symbol count)", "symbolic_L")
        add_entry("MSE max scale (τ max)", "mse_max_scale")
        lf.columnconfigure(1, weight=1)

    def _build_lyapunov_section(self, outer: tk.Frame) -> None:
        lf = tk.LabelFrame(outer, text="Lyapunov exponents", padx=10, pady=10)
        lf.pack(fill=tk.X, pady=(0, 8))
        curr = copy.deepcopy(app_config.current["lyapunov"])
        row = 0

        slopes: List[Any] = curr["rosenstein_slope_periods"]
        slope_str = ", ".join(str(x) for x in slopes)

        tk.Label(lf, text="Rosenstein slope periods (comma-separated)").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
        )
        v_slopes = tk.StringVar(value=slope_str)
        self._lyapunov_vars["rosenstein_slope_periods"] = v_slopes
        tk.Entry(lf, textvariable=v_slopes, width=22).grid(
            row=row, column=1, sticky=tk.W, pady=4
        )
        row += 1

        tk.Label(lf, text="Rosenstein mean period").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
        )
        v_mp = tk.StringVar(value=str(curr["rosenstein_mean_period"]))
        self._lyapunov_vars["rosenstein_mean_period"] = v_mp
        tk.Entry(lf, textvariable=v_mp, width=16).grid(
            row=row, column=1, sticky=tk.W, pady=4
        )
        row += 1

        tk.Label(lf, text="Wolf evolve (samples)").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
        )
        v_ev = tk.StringVar(value=str(curr["wolf_evolve"]))
        self._lyapunov_vars["wolf_evolve"] = v_ev
        tk.Entry(lf, textvariable=v_ev, width=16).grid(
            row=row, column=1, sticky=tk.W, pady=4
        )
        lf.columnconfigure(1, weight=1)

    def _build_rqa_section(self, outer: tk.Frame) -> None:
        lf = tk.LabelFrame(outer, text="Recurrence quantification (RQA)", padx=10, pady=10)
        lf.pack(fill=tk.X, pady=(0, 8))
        curr = copy.deepcopy(app_config.current["rqa"])
        row = 0

        def add_entry(label: str, key: str) -> None:
            nonlocal row
            tk.Label(lf, text=label).grid(
                row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            var = tk.StringVar(value=str(curr[key]))
            self._rqa_vars[key] = var
            tk.Entry(lf, textvariable=var, width=16).grid(
                row=row, column=1, sticky=tk.W, pady=4
            )
            row += 1

        add_entry("Z-score normalize (0 or 1)", "zscore")
        add_entry("Minimum diagonal/vertical line length", "line_length")
        add_entry("Threshold value (radius / recurrence target)", "set_value")

        def add_combo(label: str, key: str, choices: tuple[str, ...]) -> None:
            nonlocal row
            tk.Label(lf, text=label).grid(
                row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            val = str(curr[key])
            var = tk.StringVar(value=val)
            self._rqa_vars[key] = var
            vals = list(choices)
            if val not in vals:
                vals = [val] + vals
            ttk.Combobox(
                lf,
                textvariable=var,
                values=vals,
                state="readonly",
                width=14,
            ).grid(row=row, column=1, sticky=tk.W, pady=4)
            row += 1

        add_combo("Distance norm", "norm", self._RQA_NORM_CHOICES)
        add_combo("Threshold mode", "set_para", self._RQA_SETPARA_CHOICES)
        lf.columnconfigure(1, weight=1)
