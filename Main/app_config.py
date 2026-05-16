"""Application settings: defaults, merge, and JSON persistence.

Analysis code reads from :data:`current`. Nested defaults mirror
``Main/GUI_Tabs/Tab3/Analysis_code.py``. ``octave_executable`` is the optional
full path to ``octave-cli`` for OMX (empty string = auto-detect).
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

BUNDLED_TEST_SAMPLE_OMX = "Test_Sample_Data.OMX"

JsonDict = Dict[str, Any]

DEFAULTS: JsonDict = {
    "walking": {
        "min_amp": 0.3,
        "min_duration_s": 3,
        "delta": 20,
        "alpha": 1.6,
        "beta": 2.5,
        "step_freq_low": 1.4,
        "step_freq_high": 2.3,
        "wavelet_type_straight": "gaus1",
        "wavelet_type_turning": "gaus1",
    },
    "phase_space": {
        "ami_max_lag": 35,
        "fnn_max_dim": 30,
        "fnn_rtol": 15,
        "fnn_atol": 2,
        "fnn_speed": 0,
    },
    "entropy": {
        "m": 2,
        "r": 0.2,
        "symbolic_L": 2,
        "mse_max_scale": 20,
    },
    "lyapunov": {
        "rosenstein_slope_periods": [1, 2, 3, 4],
        "rosenstein_mean_period": 1,
        "wolf_evolve": 2,
    },
    "rqa": {
        "zscore": 1,
        "norm": "NON",
        "line_length": 1,
        "set_para": "radius",
        "set_value": 1,
    },
    "auto_analysis": {
        "sample_seconds": 30,
        "random_seed": 42,
    },
    # Full path to octave-cli; persisted for frozen apps with minimal PATH.
    "octave_executable": "",
}

current: JsonDict = copy.deepcopy(DEFAULTS)


def default_settings_path() -> Path:
    """User config file path (macOS and Windows via Path.home())."""
    return Path.home() / ".mcroberts_analysis" / "settings.json"


def bundled_test_sample_omx() -> Optional[Path]:
    """Path to the small OMX shipped inside PyInstaller builds (and in dev from ``Data/OMX_Files``)."""
    if getattr(sys, "frozen", False):
        p = Path(sys._MEIPASS) / "Data" / "OMX_Files" / BUNDLED_TEST_SAMPLE_OMX
    else:
        p = Path(__file__).resolve().parent.parent / "Data" / "OMX_Files" / BUNDLED_TEST_SAMPLE_OMX
    return p if p.is_file() else None


def _deep_merge(base: JsonDict, overrides: JsonDict) -> JsonDict:
    """Merge ``overrides`` into a copy of ``base`` (only keys that exist in ``base``)."""
    out = copy.deepcopy(base)
    for key, val in overrides.items():
        if key not in out:
            continue
        if isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def effective(overrides: Optional[JsonDict]) -> JsonDict:
    """Return ``DEFAULTS`` with ``overrides`` applied (missing keys stay at defaults)."""
    if not overrides:
        return copy.deepcopy(DEFAULTS)
    return _deep_merge(DEFAULTS, overrides)


def load(path: Optional[Union[str, Path]] = None) -> JsonDict:
    """Load settings from JSON. Missing file or bad JSON yields a full default copy."""
    path = Path(path) if path else default_settings_path()
    if not path.is_file():
        return copy.deepcopy(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(DEFAULTS)
    if not isinstance(raw, dict):
        return copy.deepcopy(DEFAULTS)
    return effective(raw)


def load_into_current(path: Optional[Union[str, Path]] = None) -> Optional[str]:
    """Merge saved JSON into :data:`current`.

    If there is no file, does nothing and returns ``None``. If the file exists but is
    unreadable or not a JSON object, leaves :data:`current` unchanged and returns a
    short message for a one-shot UI warning.
    """
    path = Path(path) if path else default_settings_path()
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return f"Could not read settings file; using defaults.\n\n{path}"
    if not isinstance(raw, dict):
        return f"Settings file must contain a JSON object; using defaults.\n\n{path}"
    merged = effective(raw)
    for key in DEFAULTS:
        current[key] = copy.deepcopy(merged[key])
    return None


def save(settings: JsonDict, path: Optional[Union[str, Path]] = None) -> None:
    """Write ``settings`` to JSON (creates parent directory if needed)."""
    path = Path(path) if path else default_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)
