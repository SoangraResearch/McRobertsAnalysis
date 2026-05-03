"""Settings / configuration tab."""

from __future__ import annotations

import copy
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Tuple

from Main import app_config
from Main.GUI_Tabs.gui_style import make_action_button


class Tab6Controller:
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
        container = tk.Frame(self.tab)
        container.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(container)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(4, 10))
        self._build_button_row(btn_frame)

        main = tk.Frame(container)
        main.pack(fill=tk.BOTH, expand=True)

        try:
            canvas_bg = self.tab.cget("bg")
        except tk.TclError:
            canvas_bg = None

        canvas = tk.Canvas(
            main,
            highlightthickness=0,
            bd=0,
            background=canvas_bg,
        )
        vsb = ttk.Scrollbar(main, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        scrollable = tk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=scrollable, anchor=tk.NW)

        def _on_scrollable_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfigure(canvas_window, width=max(1, int(event.width)))

        scrollable.bind("<Configure>", _on_scrollable_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _wheel(event: tk.Event) -> None:
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
                return
            if event.num == 5:
                canvas.yview_scroll(1, "units")
                return
            if sys.platform == "darwin":
                canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        for widget in (canvas, scrollable):
            widget.bind("<MouseWheel>", _wheel)
            widget.bind("<Button-4>", _wheel)
            widget.bind("<Button-5>", _wheel)

        outer = tk.Frame(scrollable)
        outer.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self._build_walking_section(outer)
        self._build_phase_space_section(outer)
        self._build_entropy_section(outer)
        self._build_lyapunov_section(outer)
        self._build_rqa_section(outer)

        def _bind_wheel_recursive(widget: tk.Misc) -> None:
            widget.bind("<MouseWheel>", _wheel)
            widget.bind("<Button-4>", _wheel)
            widget.bind("<Button-5>", _wheel)
            for child in widget.winfo_children():
                _bind_wheel_recursive(child)

        _bind_wheel_recursive(outer)

    def _build_button_row(self, parent: tk.Frame) -> None:
        make_action_button(
            parent,
            text="Apply & save",
            command=self._on_apply_save,
        ).pack(side=tk.LEFT, padx=(0, 8))
        make_action_button(
            parent,
            text="Reset to defaults",
            command=self._on_reset_defaults,
        ).pack(side=tk.LEFT, padx=(0, 8))

    def _on_apply_save(self) -> None:
        try:
            parsed = self._parse_all()
        except ValueError as e:
            messagebox.showerror("Invalid settings", str(e), parent=self.tab)
            return
        # Only update keys this tab edits so other DEFAULTS (e.g. octave_executable)
        # are not dropped or required in _parse_all().
        for key, val in parsed.items():
            app_config.current[key] = copy.deepcopy(val)
        try:
            app_config.save(app_config.current)
        except OSError as e:
            messagebox.showerror("Save failed", str(e), parent=self.tab)
            return
        messagebox.showinfo("Settings", "Settings saved.", parent=self.tab)

    def _on_reset_defaults(self) -> None:
        for key in app_config.DEFAULTS:
            app_config.current[key] = copy.deepcopy(app_config.DEFAULTS[key])
        try:
            app_config.save(app_config.current)
        except OSError as e:
            messagebox.showerror("Save failed", str(e), parent=self.tab)
            return
        self._load_widgets_from_config()
        messagebox.showinfo(
            "Settings", "Restored defaults and saved.", parent=self.tab
        )

    def _load_widgets_from_config(self) -> None:
        w = app_config.current["walking"]
        for key in (
            "min_amp",
            "min_duration_s",
            "delta",
            "alpha",
            "beta",
            "step_freq_low",
            "step_freq_high",
            "wavelet_type_straight",
            "wavelet_type_turning",
        ):
            self._walking_vars[key].set(str(w[key]))

        ps = app_config.current["phase_space"]
        for key in ps:
            self._phase_space_vars[key].set(str(ps[key]))

        ent = app_config.current["entropy"]
        for key in ent:
            self._entropy_vars[key].set(str(ent[key]))

        ly = app_config.current["lyapunov"]
        slopes = ly["rosenstein_slope_periods"]
        self._lyapunov_vars["rosenstein_slope_periods"].set(
            ", ".join(str(x) for x in slopes)
        )
        self._lyapunov_vars["rosenstein_mean_period"].set(
            str(ly["rosenstein_mean_period"])
        )
        self._lyapunov_vars["wolf_evolve"].set(str(ly["wolf_evolve"]))

        rq = app_config.current["rqa"]
        for key in rq:
            self._rqa_vars[key].set(str(rq[key]))

    @staticmethod
    def _parse_float(label: str, raw: str) -> float:
        raw = raw.strip()
        if not raw:
            raise ValueError(f"{label}: value is required.")
        try:
            return float(raw)
        except ValueError as e:
            raise ValueError(f"{label}: not a valid number.") from e

    @staticmethod
    def _parse_int(label: str, raw: str) -> int:
        raw = raw.strip()
        if not raw:
            raise ValueError(f"{label}: value is required.")
        try:
            v = int(raw, 10)
        except ValueError as e:
            raise ValueError(f"{label}: must be a whole number.") from e
        return v

    def _parse_walking(self) -> Dict[str, Any]:
        def g(key: str) -> str:
            return self._walking_vars[key].get()

        min_amp = self._parse_float("Walking / Min amplitude (g)", g("min_amp"))
        if min_amp <= 0:
            raise ValueError("Walking / Min amplitude (g): must be > 0.")

        min_dur = self._parse_int("Walking / Min walking duration (s)", g("min_duration_s"))
        if min_dur < 1:
            raise ValueError("Walking / Min walking duration (s): must be >= 1.")

        delta = self._parse_int("Walking / Peak difference", g("delta"))
        if delta < 1:
            raise ValueError("Walking / Peak difference: must be >= 1.")

        alpha = self._parse_float("Walking / Alpha", g("alpha"))
        if alpha <= 0:
            raise ValueError("Walking / Alpha: must be > 0.")

        beta = self._parse_float("Walking / Beta", g("beta"))
        if beta <= 0:
            raise ValueError("Walking / Beta: must be > 0.")

        low = self._parse_float("Walking / Step frequency low (Hz)", g("step_freq_low"))
        high = self._parse_float("Walking / Step frequency high (Hz)", g("step_freq_high"))
        if low <= 0 or high <= 0:
            raise ValueError("Walking / Step frequency: values must be > 0.")
        if low >= high:
            raise ValueError(
                "Walking / Step frequency: low must be less than high."
            )

        wt_s = g("wavelet_type_straight").strip()
        wt_t = g("wavelet_type_turning").strip()
        if not wt_s or not wt_t:
            raise ValueError("Walking / Wavelet: value is required.")

        return {
            "min_amp": min_amp,
            "min_duration_s": min_dur,
            "delta": delta,
            "alpha": alpha,
            "beta": beta,
            "step_freq_low": low,
            "step_freq_high": high,
            "wavelet_type_straight": wt_s,
            "wavelet_type_turning": wt_t,
        }

    def _parse_phase_space(self) -> Dict[str, Any]:
        def g(key: str) -> str:
            return self._phase_space_vars[key].get()

        ami = self._parse_int("Phase-space / AMI max lag", g("ami_max_lag"))
        if ami < 1:
            raise ValueError("Phase-space / AMI max lag: must be >= 1.")

        mx = self._parse_int("Phase-space / FNN max dimension", g("fnn_max_dim"))
        if mx < 2:
            raise ValueError("Phase-space / FNN max dimension: must be >= 2.")

        rtol = self._parse_int("Phase-space / FNN Rtol", g("fnn_rtol"))
        atol = self._parse_int("Phase-space / FNN Atol", g("fnn_atol"))
        if rtol < 1 or atol < 1:
            raise ValueError("Phase-space / FNN Rtol and Atol: must be >= 1.")

        speed = self._parse_float("Phase-space / FNN speed", g("fnn_speed"))

        return {
            "ami_max_lag": ami,
            "fnn_max_dim": mx,
            "fnn_rtol": rtol,
            "fnn_atol": atol,
            "fnn_speed": speed,
        }

    def _parse_entropy(self) -> Dict[str, Any]:
        def g(key: str) -> str:
            return self._entropy_vars[key].get()

        m = self._parse_int("Entropy / m", g("m"))
        if m < 1:
            raise ValueError("Entropy / m: must be >= 1.")

        r = self._parse_float("Entropy / r", g("r"))
        if r <= 0:
            raise ValueError("Entropy / r: must be > 0.")

        sym_l = self._parse_int("Entropy / Symbolic L", g("symbolic_L"))
        if sym_l < 2:
            raise ValueError("Entropy / Symbolic L: must be >= 2.")

        mse_max = self._parse_int("Entropy / MSE max scale", g("mse_max_scale"))
        if mse_max < 1:
            raise ValueError("Entropy / MSE max scale: must be >= 1.")

        return {
            "m": m,
            "r": r,
            "symbolic_L": sym_l,
            "mse_max_scale": mse_max,
        }

    def _parse_lyapunov(self) -> Dict[str, Any]:
        raw_slopes = self._lyapunov_vars["rosenstein_slope_periods"].get()
        parts = [p.strip() for p in raw_slopes.replace(";", ",").split(",") if p.strip()]
        if not parts:
            raise ValueError(
                "Lyapunov / Rosenstein slope periods: enter at least one integer."
            )
        slopes: List[int] = []
        for i, p in enumerate(parts):
            try:
                v = int(p, 10)
            except ValueError as e:
                raise ValueError(
                    f"Lyapunov / Rosenstein slope periods: invalid integer «{p}»."
                ) from e
            if v < 1:
                raise ValueError(
                    "Lyapunov / Rosenstein slope periods: each value must be >= 1."
                )
            slopes.append(v)

        mp = self._parse_int(
            "Lyapunov / Rosenstein mean period",
            self._lyapunov_vars["rosenstein_mean_period"].get(),
        )
        if mp < 1:
            raise ValueError("Lyapunov / Rosenstein mean period: must be >= 1.")

        ev = self._parse_int(
            "Lyapunov / Wolf evolve",
            self._lyapunov_vars["wolf_evolve"].get(),
        )
        if ev < 1:
            raise ValueError("Lyapunov / Wolf evolve: must be >= 1.")

        return {
            "rosenstein_slope_periods": slopes,
            "rosenstein_mean_period": mp,
            "wolf_evolve": ev,
        }

    def _parse_rqa(self) -> Dict[str, Any]:
        def g(key: str) -> str:
            return self._rqa_vars[key].get()

        z = self._parse_int("RQA / Z-score", g("zscore"))
        if z not in (0, 1):
            raise ValueError("RQA / Z-score: use 0 or 1.")

        ll = self._parse_int("RQA / Line length", g("line_length"))
        if ll < 1:
            raise ValueError("RQA / Line length: must be >= 1.")

        sv = self._parse_float("RQA / Threshold value", g("set_value"))
        if sv <= 0:
            raise ValueError("RQA / Threshold value: must be > 0.")

        norm = g("norm").strip().upper()
        if norm not in self._RQA_NORM_CHOICES:
            raise ValueError(
                f"RQA / Norm: must be one of {', '.join(self._RQA_NORM_CHOICES)}."
            )

        sp = g("set_para").strip().lower()
        if sp not in self._RQA_SETPARA_CHOICES:
            raise ValueError(
                f"RQA / Threshold mode: must be one of {', '.join(self._RQA_SETPARA_CHOICES)}."
            )

        return {
            "zscore": z,
            "norm": norm,
            "line_length": ll,
            "set_para": sp,
            "set_value": sv,
        }

    def _parse_all(self) -> Dict[str, Any]:
        return {
            "walking": self._parse_walking(),
            "phase_space": self._parse_phase_space(),
            "entropy": self._parse_entropy(),
            "lyapunov": self._parse_lyapunov(),
            "rqa": self._parse_rqa(),
        }

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

        add_entry("Embedding order m (ApEn / SampEn / PermEn / MSE)", "m")
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

        def add_combo(label: str, key: str, choices: Tuple[str, ...]) -> None:
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
