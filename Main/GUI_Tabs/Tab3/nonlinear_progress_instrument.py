"""Timing instrument for nonlinear analysis: elapsed stopwatch only.

Displays status as ``… (step/7) | Elapsed …`` during each bout’s nonlinear
sub-steps (step next to the running-step text, elapsed after ``|``).

When a run finishes, a line is appended to ``~/.mcroberts_nonlinear_run_history.txt``
with wall-clock timestamp, optional source filename, and elapsed time.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_RUN_HISTORY_FILE = Path.home() / ".mcroberts_nonlinear_run_history.txt"

_TICK_INTERVAL_S = 0.5
# Sub-steps per bout; must match Analysis_code nonlinear step sequence count.
_STEPS_PER_BOUT = 7


def _format_hms(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    s = max(0, int(round(seconds)))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def _append_run_history(
    *,
    elapsed_s: float,
    num_periods: int,
    source: Optional[str],
) -> None:
    """Append one human-readable line for finished runs (silently ignore errors)."""
    try:
        ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        el_hms = _format_hms(elapsed_s)
        src = (source or "").strip() or "unknown"
        line = (
            f"{ts}  file={src!r}  walking_bouts={int(num_periods)}  "
            f"elapsed={el_hms}"
        )
        with _RUN_HISTORY_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


class NonlinearProgressInstrument:
    """Global stopwatch for the full nonlinear run (no ETA)."""

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

        self._tick_stop = threading.Event()
        self._tick_thread: Optional[threading.Thread] = None
        self._frozen_display: Optional[str] = None
        # 1..7 while on a Period … line during an active bout (for tick + suffix).
        self._display_bout_step: Optional[int] = None

    # ---- helpers ----

    def _elapsed_s(self) -> float:
        if self._t0 is None:
            self._t0 = time.monotonic()
        return time.monotonic() - self._t0

    def _global_elapsed(self) -> float:
        if self._run_start_mono is None:
            return 0.0
        return time.monotonic() - self._run_start_mono

    def _elapsed_fragment(self) -> str:
        return f"Elapsed {_format_hms(self._global_elapsed())}"

    def _step_fragment(self) -> str:
        if self._display_bout_step is None:
            return ""
        step = max(1, min(_STEPS_PER_BOUT, int(self._display_bout_step)))
        return f" ({step}/{_STEPS_PER_BOUT})"

    def _status_tail_after_message(self) -> str:
        """Text appended after the main status message (includes step before elapsed)."""
        elapsed_f = self._elapsed_fragment()
        step_f = self._step_fragment()
        if step_f:
            return f"{step_f} | {elapsed_f}"
        return f" | {elapsed_f}"

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
                tail = self._status_tail_after_message()
                try:
                    user(f"{base_label}{tail}")
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
            self._bout_substep_index += 1
            self._display_bout_step = max(
                1, min(_STEPS_PER_BOUT, int(self._bout_substep_index))
            )
        else:
            self._display_bout_step = None

        display = message
        if self._run_start_mono is not None:
            display = f"{message}{self._status_tail_after_message()}"

        self.events.append(
            {"t_s": self._elapsed_s(), "kind": "message", "message": display}
        )
        self._send(display)

        if self._run_start_mono is not None:
            self._start_tick(message)

    def mark_run_start(self) -> None:
        """Begin wall-clock tracking for this run (call once per analysis run)."""
        self._stop_tick()
        now = time.monotonic()
        self._run_start_mono = now
        self._t0 = now
        self._frozen_display = None
        self._display_bout_step = None
        self._completed_bouts = 0
        self._bout_active = False
        self._current_bout = 0
        self._bout_substep_index = 0
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
        self._bout_active = False
        self._bout_substep_index = 0
        self._display_bout_step = None

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
        self._display_bout_step = None

        self.events.append(
            {
                "t_s": self._elapsed_s(),
                "kind": "bout_end",
                "bout_index": int(bout_index),
                "num_periods": int(num_periods),
            }
        )

    def mark_run_aborted(self) -> None:
        """Stop the stopwatch thread; run ended without :meth:`mark_run_complete`.

        Use after user cancel or other early exits so a background tick loop cannot
        keep calling the status callback after the heavy job UI has cleared.
        """
        self._stop_tick()
        self._run_start_mono = None
        self._display_bout_step = None

    def mark_run_complete(self, source: Optional[str] = None) -> None:
        """Call this after all bouts finish to append run history."""
        self._stop_tick()
        self._display_bout_step = None
        elapsed = self._global_elapsed()
        self.events.append({"t_s": self._elapsed_s(), "kind": "run_complete"})
        _append_run_history(
            elapsed_s=elapsed,
            num_periods=self._num_periods,
            source=source,
        )
        self._frozen_display = f"Complete | Elapsed {_format_hms(elapsed)}"
        self._run_start_mono = None

    def frozen_status_text(self) -> Optional[str]:
        """Last line shown after :meth:`mark_run_complete` (for frozen status UI)."""
        return self._frozen_display

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
