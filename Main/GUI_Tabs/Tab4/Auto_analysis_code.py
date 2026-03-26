import numpy as np
import pandas as pd

_ACC_COLUMNS = ["Time", "X", "Y", "Z"]


def _acc_indices_to_dataframe(acc: np.ndarray, indices: list) -> pd.DataFrame:
    """Return a copy of selected ACC rows as a DataFrame with fixed column names."""
    if not indices:
        return pd.DataFrame(columns=_ACC_COLUMNS)
    return pd.DataFrame(acc[indices], columns=_ACC_COLUMNS).reset_index(drop=True)


def split_data_by_day(data, timestamps):
    """Split ACC samples into consecutive 24-hour windows in MATLAB datenum units.

    Use the same times as ACC column 0 (``data['ACC'][:, 0]``). In MATLAB datenum,
    time is in days, so ``+ 1.0`` is one full day, not “1 o’clock.”

    Day boundaries are anchored to the **first** sample: ``timestamps[0] + 1.0``,
    ``timestamps[0] + 2.0``, ``+ 3.0``, … The walk stays in one chunk until the
    *next* sample’s time reaches or passes the current boundary; that next sample
    opens the following chunk.

    Args:
        data: Dict-like object with key ``"ACC"`` — a 2-D array with columns
            Time, X, Y, Z.
        timestamps: 1-D sequence of time values (same length as ACC rows).

    Returns:
        List of DataFrames, each with columns Time, X, Y, Z.
    """
    if "ACC" not in data:
        raise KeyError('data must contain key "ACC"')

    acc = np.asarray(data["ACC"])
    if acc.ndim != 2 or acc.shape[1] < 4:
        raise ValueError("ACC must be a 2-D array with at least 4 columns")

    ts = np.asarray(timestamps, dtype=float).ravel()
    n = ts.size
    if n == 0:
        return []
    if n != acc.shape[0]:
        raise ValueError("timestamps length must match number of ACC rows")

    chunks = []
    current_indices = []
    # End of the current window: first chunk ends one day after the first sample
    current_day_end = float(ts[0]) + 1.0

    for i in range(n):
        current_indices.append(i)
        is_last = i == n - 1
        # Start a new chunk when the next sample falls in the next day (or later)
        next_crosses_window = not is_last and float(ts[i + 1]) >= current_day_end

        if is_last or next_crosses_window:
            chunks.append(_acc_indices_to_dataframe(acc, current_indices))
            current_indices = []
            # Next window is another full day in datenum space
            current_day_end += 1.0

    return chunks
