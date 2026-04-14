"""Lightweight cooperative cancel for long Non_GUI computations (no GUI imports)."""

from __future__ import annotations

from typing import Callable, Optional


class ComputationCancelled(Exception):
    """Raised when *cancel_check* returns True during a long computation."""


def poll_cancel(cancel_check: Optional[Callable[[], bool]]) -> None:
    """If *cancel_check* is set and returns True, raise :class:`ComputationCancelled`."""
    if cancel_check is not None and cancel_check():
        raise ComputationCancelled()
