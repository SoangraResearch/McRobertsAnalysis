"""Timing and event log for nonlinear analysis (ETA groundwork).

Callers attach :class:`NonlinearProgressInstrument` to :func:`nonlinear_analysis`
via ``progress_instrument=``. User-visible status strings are unchanged; events
are recorded for future ETA logic and optional debug output.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional


class NonlinearProgressInstrument:
    """Records monotonic timestamps for run phases, bouts, and status messages."""

    def __init__(self, user_callback: Optional[Callable[[str], None]] = None) -> None:
        self._user = user_callback
        self._t0: Optional[float] = None
        self.events: List[Dict[str, Any]] = []

    def _elapsed_s(self) -> float:
        if self._t0 is None:
            self._t0 = time.monotonic()
        return time.monotonic() - self._t0

    def notify(self, message: str) -> None:
        self.events.append(
            {"t_s": self._elapsed_s(), "kind": "message", "message": message}
        )
        if self._user is not None:
            self._user(message)

    def mark_run_start(self) -> None:
        self.events.append({"t_s": self._elapsed_s(), "kind": "run_start"})

    def mark_bouts_resolved(
        self,
        *,
        num_periods: int,
        assume_walking: bool,
        total_resampled_samples: int,
        total_walking_samples: int,
    ) -> None:
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
        self.events.append(
            {
                "t_s": self._elapsed_s(),
                "kind": "bout_end",
                "bout_index": int(bout_index),
                "num_periods": int(num_periods),
            }
        )

    def summary_line(self) -> str:
        kinds = {}
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
