"""Tab 4 helpers: split OMX acceleration into day-sized windows, then run GSD per window."""
import numpy as np
import pandas as pd

from GSDA_code import gsd_iluz
from GSDB_code import gsd_low_back_acc
from ICDA_code import filter_and_print_long_segments, step_detection
from OMX_To_CSV import matlab_datenum_to_datetime

# OMX ACC block is N x 4: datenum time + three accel axes (same layout as Mobilise-D CSV export).
_ACC_COLUMNS = ["Time", "X", "Y", "Z"]
_FS = 100  # McRoberts sensor sample rate (matches Tab 2)


def _acc_indices_to_dataframe(acc: np.ndarray, indices: list) -> pd.DataFrame:
    """Return a copy of selected ACC rows as a DataFrame with fixed column names."""
    # Empty selection yields an empty frame with the right columns so callers can concat/iterate safely.
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

    # Ensure a numeric 2-D array; downstream GSD expects dense rows of Time + XYZ.
    acc = np.asarray(data["ACC"])
    if acc.ndim != 2 or acc.shape[1] < 4:
        raise ValueError("ACC must be a 2-D array with at least 4 columns")

    ts = np.asarray(timestamps, dtype=float).ravel()
    n = ts.size
    if n == 0:
        return []
    # One timestamp per ACC row (callers normally pass ACC[:, 0] as timestamps).
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


def run_sequence_detection_per_chunk(data_chunks, gsd_type, force_walking):
    """Run GSD, long-segment filtering, and step detection on each day chunk.

    Parameters match Tab 2: GSDA uses ``min_duration=30`` for long segments;
    GSDB uses the default filter; both pass ``force_walking`` into the GSD call.

    Returns:
        One dict per chunk with ``gsd_result``, ``long_segments``, step output,
        and DataFrame views for downstream steps.
    """
    results = []

    # One result entry per day chunk, in the same order as split_data_by_day().
    for idx, chunk in enumerate(data_chunks):
        if chunk is None or chunk.empty:
            # Placeholder so len(results) still matches len(data_chunks) for later stages.
            results.append(
                {
                    "chunk_index": idx,
                    "skipped": True,
                    "gsd_result": [],
                    "long_segments": [],
                    "sd_result_df": pd.DataFrame(),
                    "step_result": [],
                    "step_result_df": pd.DataFrame(),
                }
            )
            continue

        # Align with Tab 2 Mobilise-D: columns 1–3 are X, Y, Z; col 0 stays Time as datenum.
        acc = chunk.iloc[:, 1:4].to_numpy()
        time_col = chunk["Time"].to_numpy()
        # GSD APIs expect Python datetimes for logging/output metadata (not raw datenum floats).
        original_time_array = [matlab_datenum_to_datetime(t) for t in time_col]

        try:
            if gsd_type == "Healthy(GSDA)":
                # gsd_iluz expects the Mobilise-D LowerBack-style dict; we only have accel from OMX.
                imu_input = {
                    "LowerBack": {
                        "Acc": acc,
                        "Gyr": np.zeros_like(acc),
                        "Fs": {"Acc": _FS},
                    }
                }
                gsd_result, _, _ = gsd_iluz(
                    imu_input,
                    time_vector=original_time_array,
                    plot_results=False,
                    force_walking=force_walking,
                )
                # Tab 2 uses 30 s minimum bout length for GSDA when listing “long” segments.
                long_segments = filter_and_print_long_segments(
                    gsd_result,
                    original_time_array=original_time_array,
                    min_duration=30,
                )
            elif gsd_type == "Patient(GSDB)":
                gsd_result, _, _ = gsd_low_back_acc(
                    acc,
                    _FS,
                    plot_results=False,
                    time_vector=original_time_array,
                    force_walking=force_walking,
                    extra_plots=0,
                )
                # Default threshold in ICDA matches Tab 2’s GSDB path (no custom min_duration).
                long_segments = filter_and_print_long_segments(
                    gsd_result,
                    original_time_array=original_time_array,
                )
            else:
                raise ValueError(f"Unknown GSD type: {gsd_type!r}")

            sd_result_df = pd.DataFrame(gsd_result)
            # Refines each gait segment with initial-contact times; mutates segment dicts like Tab 2.
            step_result = step_detection(
                acc,
                gsd_result,
                _FS,
                plot_results=False,
                original_time_array=original_time_array,
            )
            # step_detection returns a list of dicts; empty list → empty frame for CSV/export later.
            step_result_df = (
                pd.DataFrame(step_result) if step_result else pd.DataFrame()
            )

            results.append(
                {
                    "chunk_index": idx,
                    "skipped": False,
                    "gsd_result": gsd_result,
                    "long_segments": long_segments,
                    "sd_result_df": sd_result_df,
                    "step_result": step_result,
                    "step_result_df": step_result_df,
                }
            )
        except Exception as e:
            # Re-raise with chunk index so the GUI / logs show which day failed.
            raise RuntimeError(
                f"Sequence detection failed on day chunk index {idx}"
            ) from e

    return results
