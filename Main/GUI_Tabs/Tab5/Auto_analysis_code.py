"""Tab 4 helpers: split OMX acceleration into day-sized windows, then run GSD per window."""
import os
import shutil
import tempfile
from typing import Callable, Optional

import numpy as np
import pandas as pd

from GSDA_code import gsd_iluz
from GSDB_code import gsd_low_back_acc
from ICDA_code import filter_and_print_long_segments, step_detection
from Main import app_config
from Main.GUI_Tabs.Tab3.Analysis_code import (
    NonlinearAnalysisUserCancelled,
    linear_analysis,
    nonlinear_analysis,
)
from OMX_To_CSV import matlab_datenum_to_datetime

# OMX ACC block is N x 4: datenum time + three accel axes (same layout as Mobilise-D CSV export).
_ACC_COLUMNS = ["Time", "X", "Y", "Z"]
_FS = 100  # McRoberts sensor sample rate (matches Tab 2)


class SegmentBatchCancelled(Exception):
    """User cancelled during :func:`run_segment_batch_analysis`."""

    pass


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


def select_segments_for_auto_analysis(per_chunk_results):
    """Build the list of walking bouts to analyze next (Tab 4 segment-selection step).

    Each chunk already applied ``filter_and_print_long_segments`` during sequence
    detection (same rules as Tab 2). This step only **collects** those bouts into
    one list and sorts them so later code can iterate in a stable order.

    ``segment['Start']`` / ``segment['End']`` are in **seconds from the start of
    that day chunk**, not from the beginning of the full OMX file.

    Args:
        per_chunk_results: Output of ``run_sequence_detection_per_chunk`` (list of dicts).

    Returns:
        List of dicts with ``chunk_index``, ``segment_index`` (nth long bout in
        that chunk), and ``segment`` (the original GSD segment dict).
    """
    if not per_chunk_results:
        return []

    selected = []
    for entry in per_chunk_results:
        if not entry or entry.get("skipped"):
            continue
        chunk_idx = entry["chunk_index"]
        long_segs = entry.get("long_segments") or []
        # Each item is a gait bout dict (Start/End in seconds within this chunk).
        for seg_i, segment in enumerate(long_segs):
            if not isinstance(segment, dict):
                continue
            selected.append(
                {
                    "chunk_index": chunk_idx,
                    "segment_index": seg_i,
                    "segment": segment,
                }
            )

    # Day order, then earlier bouts first within the same day (reproducible runs).
    selected.sort(
        key=lambda r: (
            r["chunk_index"],
            float(r["segment"].get("Start", 0.0)),
        )
    )
    return selected


def _write_segment_analysis_csv(chunk_df, start_s, end_s, csv_path):
    """Write one Tab-3–compatible CSV (Time, Ax, Ay, Az) for samples in [start_s, end_s).

    ``start_s`` / ``end_s`` are seconds from the beginning of ``chunk_df`` (same as GSD).
    Indices follow ``step_detection``: ``round(seconds * fs)`` with end index exclusive in ``iloc``.
    """
    n = len(chunk_df)
    start_idx = int(round(float(start_s) * _FS))
    end_idx = int(round(float(end_s) * _FS))
    start_idx = max(0, min(start_idx, n))
    end_idx = max(0, min(end_idx, n))
    if end_idx <= start_idx:
        raise ValueError(
            f"segment sample range empty or invalid ({start_idx}:{end_idx} rows, n={n})"
        )

    sub = chunk_df.iloc[start_idx:end_idx]
    out = pd.DataFrame(
        {
            "Time": sub["Time"].to_numpy(),
            "Ax": sub["X"].to_numpy(),
            "Ay": sub["Y"].to_numpy(),
            "Az": sub["Z"].to_numpy(),
        }
    )
    out.to_csv(csv_path, index=False)


def run_segment_batch_analysis(
    data_chunks,
    selected_segments,
    assume_walking=True,
    progress_callback: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
):
    """Tab 3 linear + nonlinear analysis for each selected long segment.

    Each segment becomes a temporary CSV (one bout per file). ``assume_walking=True``
    treats the whole slice as walking, matching Tab 3’s checkbox when the bout is
    already chosen by GSD.

    ``progress_callback`` receives short status strings (e.g. per-segment progress
    and nonlinear sub-steps) for GUI feedback; safe to call from a worker thread
    if the callback marshals to the UI thread.

    If ``cancel_check`` returns True between segments, raises :exc:`SegmentBatchCancelled`.

    Runs on the caller’s thread. Destroys temp files when finished.

    Returns:
        List of dicts: ``chunk_index``, ``segment_index``, ``segment``, optional
        ``error`` (str if failed), else ``linear_df`` and ``nonlinear_df``.
    """
    if not selected_segments:
        return []

    results = []
    tmpdir = tempfile.mkdtemp(prefix="mcroberts_tab4_")
    nseg = len(selected_segments)
    try:
        for k, sel in enumerate(selected_segments):
            if cancel_check and cancel_check():
                raise SegmentBatchCancelled()
            if progress_callback:
                progress_callback(
                    f"Segment {k + 1}/{nseg}: linear + nonlinear analysis…"
                )
            chunk_idx = sel["chunk_index"]
            seg = sel["segment"]
            chunk_df = data_chunks[chunk_idx]
            if chunk_df is None or chunk_df.empty:
                results.append(
                    {
                        "chunk_index": chunk_idx,
                        "segment_index": sel["segment_index"],
                        "segment": seg,
                        "error": "empty day chunk",
                        "linear_df": None,
                        "nonlinear_df": None,
                    }
                )
                continue

            path = os.path.join(tmpdir, f"c{chunk_idx}_s{sel['segment_index']}_{k}.csv")
            try:
                _write_segment_analysis_csv(
                    chunk_df,
                    seg.get("Start", 0),
                    seg.get("End", 0),
                    path,
                )
            except Exception as ex:
                results.append(
                    {
                        "chunk_index": chunk_idx,
                        "segment_index": sel["segment_index"],
                        "segment": seg,
                        "error": str(ex),
                        "linear_df": None,
                        "nonlinear_df": None,
                    }
                )
                continue

            try:
                lin_df, _plots = linear_analysis(
                    path,
                    None,
                    assume_walking,
                    build_plots=False,
                    settings=app_config.current,
                )

                def _nlin_progress(msg: str) -> None:
                    if progress_callback:
                        progress_callback(
                            f"Segment {k + 1}/{nseg}: {msg}"
                        )

                nlin_df, _raw = nonlinear_analysis(
                    path,
                    assume_walking,
                    progress_callback=_nlin_progress if progress_callback else None,
                    settings=app_config.current,
                    cancel_check=cancel_check,
                )
            except NonlinearAnalysisUserCancelled:
                raise SegmentBatchCancelled()
            except Exception as ex:
                results.append(
                    {
                        "chunk_index": chunk_idx,
                        "segment_index": sel["segment_index"],
                        "segment": seg,
                        "error": str(ex),
                        "linear_df": None,
                        "nonlinear_df": None,
                    }
                )
                continue

            results.append(
                {
                    "chunk_index": chunk_idx,
                    "segment_index": sel["segment_index"],
                    "segment": seg,
                    "error": None,
                    "linear_df": lin_df,
                    "nonlinear_df": nlin_df,
                }
            )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return results


def combine_segment_batch_results_to_tables(batch_results):
    """Flatten per-segment analysis results into 2 combined tables.

    The batch results come from :func:`run_segment_batch_analysis` and contain
    ``linear_df`` and ``nonlinear_df`` for each successfully analyzed segment.

    Returns:
        (linear_all_df, nonlinear_all_df, failures)
        - ``linear_all_df``: concatenated linear segment rows with metadata
        - ``nonlinear_all_df``: concatenated nonlinear segment rows with metadata
        - ``failures``: list of dicts describing segments that errored
    """
    linear_parts = []
    nonlinear_parts = []
    failures = []

    for r in batch_results or []:
        if not r:
            continue

        if r.get("error") is not None:
            failures.append(
                {
                    "chunk_index": r.get("chunk_index"),
                    "segment_index": r.get("segment_index"),
                    "error": r.get("error"),
                }
            )
            continue

        chunk_idx = r.get("chunk_index")
        seg_idx = r.get("segment_index")
        seg = r.get("segment") or {}

        start_s = seg.get("Start")
        end_s = seg.get("End")
        try:
            duration_s = float(end_s) - float(start_s)
        except Exception:
            duration_s = None

        meta = {
            "chunk_index": chunk_idx,
            "segment_index": seg_idx,
            "segment_start_s": start_s,
            "segment_end_s": end_s,
            "segment_duration_s": duration_s,
        }

        linear_df = r.get("linear_df")
        if isinstance(linear_df, pd.DataFrame) and not linear_df.empty:
            df = linear_df.copy()
            for k, v in meta.items():
                df[k] = v
            linear_parts.append(df)

        nonlinear_df = r.get("nonlinear_df")
        if isinstance(nonlinear_df, pd.DataFrame) and not nonlinear_df.empty:
            df = nonlinear_df.copy()
            for k, v in meta.items():
                df[k] = v
            nonlinear_parts.append(df)

    linear_all = (
        pd.concat(linear_parts, ignore_index=True) if linear_parts else pd.DataFrame()
    )
    nonlinear_all = (
        pd.concat(nonlinear_parts, ignore_index=True)
        if nonlinear_parts
        else pd.DataFrame()
    )

    return linear_all, nonlinear_all, failures


def combine_tab2_per_chunk_export_tables(per_chunk_results):
    """Stack Tab 2–style tables from each day chunk for export.

    Each row’s gait timing fields (e.g. Start/End in ``sd_result_df``) stay in
    **seconds from the start of that day chunk**, same as Tab 2 on a CSV that
    contains only that chunk.

    Returns:
        (gsd_all_df, step_all_df): combined GSD results and step-detection tables,
        with column ``day_chunk_index`` identifying the source chunk (0-based).
    """
    gsd_parts = []
    step_parts = []

    for entry in per_chunk_results or []:
        if not entry or entry.get("skipped"):
            continue
        idx = entry.get("chunk_index")
        sdf = entry.get("sd_result_df")
        if isinstance(sdf, pd.DataFrame) and not sdf.empty:
            d = sdf.copy()
            d["day_chunk_index"] = idx
            gsd_parts.append(d)
        pdf = entry.get("step_result_df")
        if isinstance(pdf, pd.DataFrame) and not pdf.empty:
            d = pdf.copy()
            d["day_chunk_index"] = idx
            step_parts.append(d)

    gsd_all = (
        pd.concat(gsd_parts, ignore_index=True) if gsd_parts else pd.DataFrame()
    )
    step_all = (
        pd.concat(step_parts, ignore_index=True) if step_parts else pd.DataFrame()
    )
    return gsd_all, step_all
