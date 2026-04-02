# -*- mode: python ; coding: utf-8 -*-
# macOS .app: pyinstaller "McRoberts Analysis.spec" --clean
# Windows folder + .exe: same command (BUNDLE runs only on darwin).
#
# Run PyInstaller with the same Python interpreter / venv / conda env that has
# octave_kernel, oct2py, ssqueezepy, and the rest of the app dependencies.

import importlib.util
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.abspath('.')


def _pkg_root(pkg_name: str) -> Path:
    spec = importlib.util.find_spec(pkg_name)
    if spec is None:
        raise RuntimeError(
            f"Package '{pkg_name}' is not installed in this Python environment. "
            "Activate the env with your project dependencies, then rebuild."
        )
    if spec.submodule_search_locations:
        return Path(list(spec.submodule_search_locations)[0])
    if spec.origin:
        return Path(spec.origin).parent
    raise RuntimeError(f"Cannot locate install path for '{pkg_name}'.")


def _require_pkg_file(pkg_name: str, *relative_parts: str) -> str:
    path = _pkg_root(pkg_name).joinpath(*relative_parts)
    if not path.is_file():
        raise FileNotFoundError(
            f"Expected file missing: {path}\n"
            f"Reinstall or upgrade the '{pkg_name}' package in this environment."
        )
    return str(path)


# macOS .app: Tk often exits immediately if Tcl/Tk data is not fully bundled (GitHub Actions / framework Python).
_extra_binaries = []
_extra_datas = []
if sys.platform == 'darwin':
    try:
        from PyInstaller.utils.hooks import collect_all

        _tk_d, _tk_b, _ = collect_all('tkinter')
        _extra_datas.extend(_tk_d)
        _extra_binaries.extend(_tk_b)
    except Exception as e:
        print(f"[McRoberts Analysis.spec] tkinter collect_all failed: {e}", file=sys.stderr)

# oct2py (and similar) call importlib.metadata.version(...) at import time; PyInstaller omits .dist-info unless copied.
def _copy_pkg_metadata(*pkg_names: str) -> list:
    from PyInstaller.utils.hooks import copy_metadata

    out = []
    for name in pkg_names:
        try:
            out.extend(copy_metadata(name))
        except Exception as e:
            print(f"[McRoberts Analysis.spec] copy_metadata({name}) failed: {e}", file=sys.stderr)
    return out


_metadata_datas = _copy_pkg_metadata(
    "oct2py",
    "octave_kernel",
    "ssqueezepy",
    "metakernel",  # oct2py → metakernel; __init__ calls importlib.metadata.version("metakernel")
)

a = Analysis(
    ['Main/GUI_Main.py'],
    pathex=[PROJECT_ROOT, os.path.join(PROJECT_ROOT, 'Main')],
    binaries=_extra_binaries,
    datas=[
        # Data files the app needs at runtime
        ('Mobilise-D-TVS-Recommended-Algorithms-master/ICDA/Library/FIR-2-3Hz-40.mat',
         'Mobilise-D-TVS-Recommended-Algorithms-master/ICDA/Library'),
        ('DynaportCompany_Codes_new/source', 'DynaportCompany_Codes_new/source'),
        # Only the two gait modules are used; gait_functions/forest-develop is an unused vendored
        # tree that also triggered shutil copy failures (errno 89) on some macOS setups.
        (
            os.path.join(PROJECT_ROOT, 'Non_GUI/Analysis_Code/gait_functions/walking.py'),
            'Non_GUI/Analysis_Code/gait_functions',
        ),
        (
            os.path.join(PROJECT_ROOT, 'Non_GUI/Analysis_Code/gait_functions/hs_to_detection.py'),
            'Non_GUI/Analysis_Code/gait_functions',
        ),
        ('Non_GUI/Analysis_Code/non_linear_functions', 'Non_GUI/Analysis_Code/non_linear_functions'),
        ('Non_GUI/Analysis_Code/forest_develop/src/forest', 'Non_GUI/Analysis_Code/forest_develop/src/forest'),
        # Package files PyInstaller misses (paths resolved from the active interpreter)
        (_require_pkg_file('octave_kernel', 'kernel.json'), 'octave_kernel'),
        (_require_pkg_file('ssqueezepy', 'configs.ini'), 'ssqueezepy'),
        (_require_pkg_file('oct2py', '_pyeval.m'), 'oct2py'),
    ]
    + _extra_datas
    + _metadata_datas,
    hiddenimports=[
        # All imports listed explicitly (no __init__.py files in project)
        'Main.ICDA_code',
        'Main.GSDA_code',
        'Main.GSDB_code',
        'Main.GSD_plots',
        'Main.OMX_To_CSV',
        'OMX_To_CSV',
        'GSDA_code',
        'GSDB_code',
        'ICDA_code',
        'GSD_plots',
        'Main.GUI_Tabs.Tab1.Tab1Controller',
        'Main.GUI_Tabs.Tab1.Acceleration_Plot',
        'Main.GUI_Tabs.Tab2.Tab2Controller',
        'Main.GUI_Tabs.Tab3.Tab3Controller',
        'Main.GUI_Tabs.Tab3.Analysis_code',
        'Main.GUI_Tabs.Tab3.Analysis_Plots',
        'Main.GUI_Tabs.Tab4.Auto_analysis_code',
        'Main.GUI_Tabs.Tab4.auto_analysis_progress',
        'Non_GUI.Analysis_Code.gait_functions.walking',
        'Non_GUI.Analysis_Code.gait_functions.hs_to_detection',
        'Non_GUI.Analysis_Code.non_linear_functions.ami_stergio',
        'Non_GUI.Analysis_Code.non_linear_functions.fnn',
        'Non_GUI.Analysis_Code.non_linear_functions.ent_Ap',
        'Non_GUI.Analysis_Code.non_linear_functions.ent_symbolic',
        'Non_GUI.Analysis_Code.non_linear_functions.entMSPlus',
        'Non_GUI.Analysis_Code.non_linear_functions.entPermu',
        'Non_GUI.Analysis_Code.non_linear_functions.lye_R',
        'Non_GUI.Analysis_Code.non_linear_functions.lye_W',
        'Non_GUI.Analysis_Code.non_linear_functions.rqa',
        'Non_GUI.Analysis_Code.non_linear_functions.ent_Samp',
        'Non_GUI.Analysis_Code.forest_develop.src.forest.constants',
        'Non_GUI.Analysis_Code.forest_develop.src.forest.utils',
        'pandas',
        'numpy',
        'scipy',
        'scipy.signal',
        'scipy.interpolate',
        'scipy.io',
        'scipy.sparse',
        'scipy.stats',
        'scipy.spatial.distance',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'matplotlib.figure',
        'pywt',
        'oct2py',
        'dateutil',
        'dateutil.tz',
        'ssqueezepy',
        'skimage',
        'skimage.transform',
        'sklearn',
        'sklearn.metrics',
        'sklearn.metrics.pairwise',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.ttk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='McRoberts Analysis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='McRoberts Analysis',
)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='McRoberts Analysis.app',
        icon=None,
        bundle_identifier='com.mcroberts.analysis',
    )
