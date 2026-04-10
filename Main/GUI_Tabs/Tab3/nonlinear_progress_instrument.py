"""Timing instrument for nonlinear analysis: elapsed stopwatch + estimated total.

Displays two time values alongside each step label:
  - **Elapsed**: wall time since the run started (always truthful, only goes up)
  - **Est. total**: predicted wall time for the entire run (all bouts), frozen
    after timing data allows a good guess.

  **Multi-bout runs:** calibration is not applied at start (it is biased by short
  bouts). After the **first** walking bout finishes, we measure each of the seven
  sub-step durations, then extrapolate later bouts with
  ``t_k ≈ t_1 * (n_k / n_1) ** p`` per step (stronger ``p`` for RQA/MSE).

  **Single-bout runs:** if ``~/.mcroberts_nonlinear_calibration.json`` exists,
  estimate is locked immediately from saved rate × planned work; otherwise it
  locks after the bout completes (``Est. total ≈ elapsed``).

  Calibration is still updated at the end of every run for single-bout use.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_CALIBRATION_FILE = Path.home() / ".mcroberts_nonlinear_calibration.json"

_STEPS_PER_BOUT = 7
_TICK_INTERVAL_S = 0.5
# Single-bout files longer than this (seconds of walking at 100 Hz) skip file calibration
# at start — short-file rates badly underestimate RQA/MSE cost on long series.
_LONG_SINGLE_BOUT_MIN_S = 180.0

# Order must match Analysis_code nonlinear step sequence.
_STEP_ORDER = ("AMI", "FNN", "ENT", "LYE_R", "LYE_W", "RQA", "MSE")

# Relative complexity by step type. RQA/MSE are intentionally heavier.
_STEP_WEIGHT = {
    "AMI": 1.0,
    "FNN": 1.6,
    "ENT": 1.8,
    "LYE_R": 1.9,
    "LYE_W": 1.5,
    "RQA": 5.8,
    "MSE": 4.2,
}

# Nonlinear length scaling (used for calibration weighted units).
_STEP_EXPONENT = {
    "AMI": 1.00,
    "FNN": 1.05,
    "ENT": 1.00,
    "LYE_R": 1.08,
    "LYE_W": 1.06,
    "RQA": 1.35,
    "MSE": 1.25,
}

# Extrapolate remaining bouts from first-bout timings (often superlinear in n).
_EXTRAPOLATE_EXPONENT = {
    "AMI": 1.00,
    "FNN": 1.05,
    "ENT": 1.00,
    "LYE_R": 1.10,
    "LYE_W": 1.08,
    "RQA": 1.95,
    "MSE": 1.38,
}


def _format_hms(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    s = max(0, int(round(seconds)))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def _load_calibration() -> Optional[float]:
    """Return saved seconds-per-weighted-unit, or None if not available."""
    try:
        data = json.loads(_CALIBRATION_FILE.read_text())
        rate = float(data["seconds_per_unit"])
        if rate > 0:
            return rate
    except Exception:
        pass
    return None


def _save_calibration(seconds_per_unit: float) -> None:
    """Persist calibration rate to disk (silently ignore errors)."""
    try:
        _CALIBRATION_FILE.write_text(
            json.dumps({"seconds_per_unit": seconds_per_unit}, indent=2)
        )
    except Exception:
        pass


class NonlinearProgressInstrument:
    """Global stopwatch + frozen estimated total for the full nonlinear run."""

    def __init__(self, user_callback: Optional[Callable[[str], None]] = None) -> None:
        self._user = user_callback
        self._t0: Optional[float] = None
        self.events: List[Dict[str, Any]] = []

        self._run_start_mono: Optional[float] = None
        self._num_periods: int = 0
        self._completed_bouts: int = 0
        self._bout_active: bool = False
        self._current_bout: int = 0
        self._bout_substep_index: int = 0
        self._current_bout_data_len: int = 0

        self._total_substeps_done: int = 0
        self._weighted_units_done: float = 0.0
        self._total_weighted_units: float = 0.0
        self._estimated_total_s: Optional[float] = None
        self._estimate_locked: bool = False

        self._walking_bout_samples: List[int] = []
        self._calibration_rate: Optional[float] = _load_calibration()

        self._bout0_step_seconds: Dict[str, float] = {}
        self._step_start_mono: Optional[float] = None
        self._single_bout_long: bool = False

        self._tick_stop = threading.Event()
        self._tick_thread: Optional[threading.Thread] = None

    # ---- helpers ----

    def _elapsed_s(self) -> float:
        if self._t0 is None:
            self._t0 = time.monotonic()
        return time.monotonic() - self._t0

    def _global_elapsed(self) -> float:
        if self._run_start_mono is None:
            return 0.0
        return time.monotonic() - self._run_start_mono

    @staticmethod
    def _step_units(step_name: str, bout_samples: int) -> float:
        n = float(max(1, int(bout_samples)))
        w = float(_STEP_WEIGHT.get(step_name, 1.0))
        p = float(_STEP_EXPONENT.get(step_name, 1.0))
        return w * (n ** p)

    def _total_units_for_bout(self, bout_samples: int) -> float:
        return sum(self._step_units(step, bout_samples) for step in _STEP_ORDER)

    def _completed_step_name_from_index(self, completed_step_idx_1based: int) -> str:
        ix = max(1, min(_STEPS_PER_BOUT, int(completed_step_idx_1based))) - 1
        return _STEP_ORDER[ix]

    def _recompute_total_weighted_units(self) -> None:
        if self._walking_bout_samples:
            self._total_weighted_units = float(
                sum(self._total_units_for_bout(n) for n in self._walking_bout_samples)
            )
            return

        # Fallback when explicit per-bout lengths were not provided.
        if self._num_periods <= 0:
            self._total_weighted_units = 0.0
            return
        self._total_weighted_units = float(self._num_periods * len(_STEP_ORDER))

    def _lock_estimate_from_calibration(self) -> bool:
        """If calibration exists, compute and lock estimate immediately. Returns True if locked."""
        if self._calibration_rate is None:
            return False
        if self._total_weighted_units <= 0:
            return False
        self._estimated_total_s = self._calibration_rate * self._total_weighted_units
        self._estimate_locked = True
        return True

    def _compute_and_lock_estimated_total(self) -> None:
        """Compute the estimated total from real elapsed time and freeze it."""
        if self._estimate_locked:
            return
        if self._run_start_mono is None:
            return
        elapsed = self._global_elapsed()
        if elapsed <= 0:
            return

        if self._weighted_units_done > 1e-9 and self._total_weighted_units > 1e-9:
            per_unit = elapsed / self._weighted_units_done
            self._estimated_total_s = per_unit * self._total_weighted_units
        elif self._total_substeps_done >= 1 and self._num_periods > 0:
            total_substeps = self._num_periods * _STEPS_PER_BOUT
            per_step = elapsed / float(self._total_substeps_done)
            self._estimated_total_s = per_step * float(total_substeps)
        else:
            return

        self._estimate_locked = True

    def _try_lock_from_first_bout_extrapolation(self) -> None:
        """After bout 0 ends: set Est. total from measured step times + length scaling."""
        if self._run_start_mono is None:
            return
        elapsed = self._global_elapsed()
        if elapsed <= 0:
            return

        n_periods = self._num_periods
        if n_periods <= 0:
            return

        if n_periods >= 2:
            if (
                len(self._walking_bout_samples) < n_periods
                or len(self._bout0_step_seconds) < _STEPS_PER_BOUT
            ):
                self._compute_and_lock_estimated_total()
                return
            n1 = float(self._walking_bout_samples[0])
            if n1 < 1.0:
                self._compute_and_lock_estimated_total()
                return
            remaining = 0.0
            for j in range(1, n_periods):
                nj = float(self._walking_bout_samples[j])
                ratio = max(nj / n1, 1e-9)
                for step in _STEP_ORDER:
                    t1 = self._bout0_step_seconds.get(step)
                    if t1 is None or t1 <= 0:
                        continue
                    p = float(_EXTRAPOLATE_EXPONENT.get(step, 1.0))
                    remaining += t1 * (ratio**p)
            self._estimated_total_s = elapsed + max(0.0, remaining)
            self._estimate_locked = True
            return

        # Single bout: total time is essentially elapsed when the bout's math is done.
        self._estimated_total_s = elapsed
        self._estimate_locked = True

    def _maybe_lock_long_single_bout_midway(self) -> None:
        """Long single-bout run: lock once after RQA completes (heavy work mostly done)."""
        if self._num_periods != 1 or not self._single_bout_long:
            return
        if self._estimate_locked:
            return
        if self._bout_substep_index < 7:
            return
        if self._weighted_units_done <= 1e-9 or self._total_weighted_units <= 1e-9:
            return
        elapsed = self._global_elapsed()
        if elapsed <= 0:
            return
        self._estimated_total_s = (
            elapsed / self._weighted_units_done * self._total_weighted_units
        )
        self._estimate_locked = True

    def _build_suffix(self) -> str:
        elapsed = self._global_elapsed()
        parts = [f"Elapsed {_format_hms(elapsed)}"]
        if self._estimated_total_s is not None and self._estimated_total_s > 0:
            parts.append(f"Est. total {_format_hms(self._estimated_total_s)}")
        return " | ".join(parts)

    def _send(self, text: str) -> None:
        if self._user is not None:
            try:
                self._user(text)
            except Exception:
                pass

    # ---- tick thread (stopwatch) ----

    def _stop_tick(self) -> None:
        self._tick_stop.set()
        t = self._tick_thread
        self._tick_thread = None
        if t is not None and t.is_alive():
            t.join(timeout=1.0)

    def _start_tick(self, base_label: str) -> None:
        self._stop_tick()
        self._tick_stop = threading.Event()
        user = self._user
        if user is None:
            return

        def loop() -> None:
            while not self._tick_stop.wait(_TICK_INTERVAL_S):
                suffix = self._build_suffix()
                try:
                    user(f"{base_label} | {suffix}")
                except Exception:
                    break

        th = threading.Thread(target=loop, daemon=True, name="nonlinear_stopwatch")
        th.start()
        self._tick_thread = th

    # ---- public API ----

    def notify(self, message: str) -> None:
        """Called by Analysis_code for step labels and summary lines."""
        self._stop_tick()

        is_period_line = self._bout_active and message.startswith("Period ")
        if is_period_line:
            now_mono = time.monotonic()
            self._bout_substep_index += 1
            if self._current_bout == 0:
                if self._bout_substep_index == 1:
                    self._step_start_mono = now_mono
                elif self._bout_substep_index > 1:
                    completed_idx = self._bout_substep_index - 1
                    step_name = self._completed_step_name_from_index(completed_idx)
                    if self._step_start_mono is not None:
                        self._bout0_step_seconds[step_name] = max(
                            now_mono - self._step_start_mono, 1e-6
                        )
                    self._step_start_mono = now_mono
            if self._bout_substep_index > 1:
                completed_idx = self._bout_substep_index - 1
                step_name = self._completed_step_name_from_index(completed_idx)
                self._total_substeps_done += 1
                self._weighted_units_done += self._step_units(
                    step_name, self._current_bout_data_len
                )
            self._maybe_lock_long_single_bout_midway()

        display = message
        if self._run_start_mono is not None:
            display = f"{message} | {self._build_suffix()}"

        self.events.append(
            {"t_s": self._elapsed_s(), "kind": "message", "message": display}
        )
        self._send(display)

        if self._run_start_mono is not None:
            self._start_tick(message)

    def mark_run_start(self) -> None:
        self._run_start_mono = time.monotonic()
        self.events.append({"t_s": self._elapsed_s(), "kind": "run_start"})

    def mark_bouts_resolved(
        self,
        *,
        num_periods: int,
        assume_walking: bool,
        total_resampled_samples: int,
        total_walking_samples: int,
        walking_bout_samples: Optional[List[int]] = None,
    ) -> None:
        self._stop_tick()
        self._num_periods = int(num_periods)
        self._completed_bouts = 0
        self._total_substeps_done = 0
        self._weighted_units_done = 0.0
        self._estimated_total_s = None
        self._estimate_locked = False
        self._bout_active = False
        self._bout0_step_seconds = {}
        self._step_start_mono = None
        walk_s = float(total_walking_samples) / 100.0 if total_walking_samples else 0.0
        self._single_bout_long = int(num_periods) == 1 and walk_s >= _LONG_SINGLE_BOUT_MIN_S

        if walking_bout_samples is None:
            self._walking_bout_samples = []
        else:
            self._walking_bout_samples = [max(1, int(x)) for x in walking_bout_samples]

        self._recompute_total_weighted_units()

        # Single-bout, not very long: optional immediate lock from saved calibration.
        # Multi-bout or long single-bout: skip — short-file calibration is misleading.
        if int(num_periods) < 2 and not self._single_bout_long:
            self._lock_estimate_from_calibration()

        self.events.append(
            {
                "t_s": self._elapsed_s(),
                "kind": "bouts_resolved",
                "num_periods": int(num_periods),
                "assume_walking": bool(assume_walking),
                "total_resampled_samples": int(total_resampled_samples),
                "total_walking_samples": int(total_walking_samples),
            }
        )

    def mark_bout_start(
        self, bout_index: int, num_periods: int, data_length: int
    ) -> None:
        self._stop_tick()
        self._bout_active = True
        self._current_bout = int(bout_index)
        self._bout_substep_index = 0
        self._current_bout_data_len = int(data_length)

        self.events.append(
            {
                "t_s": self._elapsed_s(),
                "kind": "bout_start",
                "bout_index": int(bout_index),
                "num_periods": int(num_periods),
                "data_length": int(data_length),
            }
        )

    def mark_bout_end(self, bout_index: int, num_periods: int) -> None:
        self._stop_tick()
        self._bout_active = False
        self._completed_bouts += 1

        trailing_steps = max(0, _STEPS_PER_BOUT - self._bout_substep_index + 1)
        for t in range(trailing_steps):
            completed_idx = self._bout_substep_index + t
            step_name = self._completed_step_name_from_index(completed_idx)
            self._total_substeps_done += 1
            self._weighted_units_done += self._step_units(
                step_name, self._current_bout_data_len
            )

        if int(bout_index) == 0:
            if self._step_start_mono is not None:
                self._bout0_step_seconds["MSE"] = max(
                    time.monotonic() - self._step_start_mono, 1e-6
                )
                self._step_start_mono = None
            self._try_lock_from_first_bout_extrapolation()
        elif not self._estimate_locked:
            self._compute_and_lock_estimated_total()

        self.events.append(
            {
                "t_s": self._elapsed_s(),
                "kind": "bout_end",
                "bout_index": int(bout_index),
                "num_periods": int(num_periods),
            }
        )

    def mark_run_complete(self) -> None:
        """Call this after all bouts finish to save calibration for future runs."""
        self._stop_tick()
        elapsed = self._global_elapsed()
        if elapsed > 0 and self._weighted_units_done > 1e-9:
            rate = elapsed / self._weighted_units_done
            _save_calibration(rate)
        self.events.append({"t_s": self._elapsed_s(), "kind": "run_complete"})

    def summary_line(self) -> str:
        kinds: Dict[str, int] = {}
        for e in self.events:
            k = e.get("kind", "?")
            kinds[k] = kinds.get(k, 0) + 1
        dt = 0.0
        if self.events:
            dt = self.events[-1]["t_s"]
        return (
            f"[nonlinear instrument] events={len(self.events)} "
            f"duration_s={dt:.3f} kinds={kinds}"
        )
