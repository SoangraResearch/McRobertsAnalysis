"""
OMX file reading via GNU Octave and Oct2Py.

Packaging note (PyInstaller / macOS .app): ``sys.frozen``, ``sys._MEIPASS``,
``base_path`` resolution, and ``_resolve_octave_executable`` exist only so the
same code runs inside a bundled app (minimal PATH, bundled Dynaport sources).
They do not change OMX parsing or numeric outputs relative to a normal dev
install when Octave is available and the same ``DynaportCompany_Codes_new``
tree is used—only how the process finds Octave and those files on disk.
"""
import inspect
import sys
import os
import atexit
import shutil
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from datetime import datetime, timedelta
from oct2py import Oct2Py


def _resolve_octave_executable():
    """Path to Octave for Oct2Py (.app / GUI convenience only).

    Does not alter OMX results—only which Octave binary is launched. macOS .app
    bundles started from Finder inherit a minimal PATH, so Homebrew Octave is
    often invisible unless we probe standard locations or the user sets
    OCTAVE_EXECUTABLE (see Main/README.md).
    """
    for key in ("OCTAVE_EXECUTABLE", "OCTAVE"):
        p = os.environ.get(key)
        if not p:
            continue
        if os.path.isfile(p):
            return p
        found = shutil.which(p)
        if found:
            return found

    for cmd in ("octave-cli", "octave"):
        found = shutil.which(cmd)
        if found:
            return found

    if sys.platform == "darwin":
        for path in (
            "/opt/homebrew/bin/octave-cli",
            "/usr/local/bin/octave-cli",
            "/opt/homebrew/bin/octave",
            "/usr/local/bin/octave",
            "/Applications/Octave.app/Contents/Resources/usr/bin/octave-cli",
        ):
            if os.path.isfile(path):
                return path

    if sys.platform == "win32":
        # Double-clicked .exe gets a short PATH; oct2py often misses Octave unless
        # OCTAVE_EXECUTABLE is set *for the whole user session* (setx + re-login).
        # Probe typical install trees (installer default + a few alternates).
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app = os.environ.get("LOCALAPPDATA", "")
        win_roots = [
            os.path.join(program_files, "GNU Octave"),
            os.path.join(program_files_x86, "GNU Octave"),
        ]
        if local_app:
            win_roots.append(os.path.join(local_app, "Programs", "GNU Octave"))

        def _first_octave_cli_under(root: str):
            if not os.path.isdir(root):
                return None
            best = None
            try:
                for dirpath, _, filenames in os.walk(root):
                    if "octave-cli.exe" not in filenames:
                        continue
                    cand = os.path.join(dirpath, "octave-cli.exe")
                    # Prefer ...\mingw64\bin\octave-cli.exe (standard layout)
                    if r"mingw64\bin" in cand.replace("/", "\\").lower():
                        return cand
                    if best is None:
                        best = cand
            except OSError:
                return None
            return best

        for gnu_root in win_roots:
            found = _first_octave_cli_under(gnu_root)
            if found:
                return found

    return None


def process_omx_file(filepath: str):
    # .app support: resolve repo/bundle root for oc.addpath only (same MATLAB
    # code; no change to extracted acceleration values vs dev when paths match).
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

    exe = _resolve_octave_executable()
    if exe:
        # Older oct2py (common in conda) has no `executable=` kwarg; it reads
        # OCTAVE_EXECUTABLE. Newer oct2py accepts both.
        os.environ.setdefault("OCTAVE_EXECUTABLE", exe)

    try:
        params = inspect.signature(Oct2Py.__init__).parameters
    except (TypeError, ValueError):
        params = {}

    try:
        if exe and "executable" in params:
            oc = Oct2Py(executable=exe)
        else:
            oc = Oct2Py()
    except Exception as e:
        raise RuntimeError(
            "GNU Octave was not found or could not start. OMX files require Octave "
            "(see Main/README.md). If Octave is installed, set the environment variable "
            "OCTAVE_EXECUTABLE to the full path of octave-cli (on macOS, apps opened "
            "from Finder do not use your shell PATH)."
        ) from e
    atexit.register(oc.exit)

    #Adding necessary filepath
    oc.addpath(os.path.join(base_path, 'DynaportCompany_Codes_new', 'source'))

    #Getting filename
    filename = os.path.splitext(os.path.basename(filepath))[0]

    info = _read_file_info(oc, filepath)
    data = _read_acceleration_data(oc, filepath, info)

    return data, filename

def matlab_datenum_to_datetime(datenum):
        days = int(datenum)
        frac = datenum % 1
        return datetime.fromordinal(days - 366) + timedelta(days=frac)

def _read_file_info(oc, filepath):
    print(f"Reading info from: {filepath}")
    tic = time.perf_counter()
    info = oc.feval(
        'OMX_readFile',
        filepath,
        1, #info = 1
        nout=1,
        struct_to_dict=False
    )
    toc = time.perf_counter()
    print(f"Read info in {toc - tic:.4f} seconds")
    return info

def _read_acceleration_data(oc, filepath, info):
    import numpy as np
    import time

    packet_info = info.packetInfo
    timestamps = packet_info[:, 1]


    last_packet_info = packet_info[-1:, :]
    try:
        last_packet_data = oc.feval(
            'OMX_readFile',
            filepath,
            0,
            last_packet_info,
            -1,
            -1,
            0,
            0,
            [1, 1, 0],
            1,
            nout=1,
            struct_to_dict=True
        )
        if last_packet_data and 'ACC' in last_packet_data:
            true_end_time = last_packet_data['ACC'][-1, 0]
        else:
            true_end_time = timestamps[-1]
    except Exception:
        true_end_time = timestamps[-1]

    total_time_start = timestamps[0]
    total_time_stop = true_end_time  

    n_chunks = 10
    total_packets = len(packet_info)
    chunk_size = total_packets // n_chunks

    acc_chunks = []
    tic = time.perf_counter()

    for i in range(n_chunks):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size if i < n_chunks - 1 else total_packets

        chunk_packet_info = packet_info[start_idx:end_idx]

        if len(chunk_packet_info) < 2:
            continue

        try:
            data_chunk = oc.feval(
                'OMX_readFile',
                filepath,
                0,
                chunk_packet_info,
                -1,
                -1,
                0,
                0,
                [1, 1, 0],
                1,
                nout=1,
                struct_to_dict=True
            )
            if data_chunk and 'ACC' in data_chunk:
                acc_chunks.append(data_chunk['ACC'])
        except Exception:
            pass

        print(f"Reading chunk: {100*(i+1)/n_chunks:.0f}%")

    toc = time.perf_counter()

    if not acc_chunks:
        raise ValueError("No acceleration data read from file!")

    combined_acc = np.vstack(acc_chunks)

    # Final debug checks
    print(f"Read data in {toc - tic:.4f} seconds")

    return {'ACC': combined_acc}