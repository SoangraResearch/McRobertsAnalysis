## Octave Set Up Instructions
This project requires GNU Octave to run Octave code via Python.

### Step 1: Install GNU Octave

- **Windows:**  
Download and install Octave from:  
[https://www.gnu.org/software/octave/download.html](https://www.gnu.org/software/octave/download.html)

- **Mac:**  
The easiest way is via [Homebrew]
Run this command in Terminal: brew install octave

Make a note of where Octave is installed.

### Step 2: Set the `OCTAVE_EXECUTABLE` Environment Variable

- On **Windows**
    In Powershell, run: setx OCTAVE_EXECUTABLE "C:\Program Files\GNU Octave\Octave-10.2.0\mingw64\bin\octave-cli.exe" (or alternative installation path)
    restart your terminal (or IDE)

- On **macOS**
    In Terminal, run: export OCTAVE_EXECUTABLE=$(which octave-cli)
    This sets the path temporarily.
    To set it permanently, add the same line to your shell config file (e.g. ~/.zshrc or ~/.bash_profile):

### Bundled app (`.exe` / `.app`) and Octave

The PyInstaller builds **do not include GNU Octave**. You still need Octave installed on the computer.

Double-clicking the **Windows `.exe`** or **macOS `.app`** starts a process with a **limited environment** (often a short `PATH`). Easiest fix: in the GUI **Select Data** tab, use **GNU Octave (required for .OMX)** — **Browse…** to `octave-cli` (Windows: `octave-cli.exe`), then **Save path**. That value is stored in **`~/.mcroberts_analysis/settings.json`** (your home directory) and is used before auto-detection.

Alternatively, set **`OCTAVE_EXECUTABLE`** to the full path of **`octave-cli`** as a **user-level** environment variable, then sign out and back in (or restart). The app also tries common install locations on Windows; see `Main/OMX_To_CSV.py` if you need details.

## Desktop builds (PyInstaller)

Standalone **Windows** and **macOS** packages are produced with [PyInstaller](https://pyinstaller.org/) using the spec file at the **repository root**: `McRoberts Analysis.spec`.

### What each platform produces

- **Windows:** Folder `dist/McRoberts Analysis/` containing `McRoberts Analysis.exe` and an `_internal/` directory. Run the `.exe` from that folder (or distribute the whole folder).
- **macOS:** `dist/McRoberts Analysis.app` — a normal app bundle.

### GitHub Actions

Workflow: **`.github/workflows/build-desktop-apps.yml`** (“Build desktop apps”).

- **When it runs:** On **push** to `main` or `master`, and when triggered manually (**Actions** → workflow → **Run workflow**).
- **Artifacts:** After a successful run, open the run in the **Actions** tab and download:
  - **McRoberts-Analysis-Windows** — Windows build folder (as uploaded from `dist/McRoberts Analysis/`).
  - **McRoberts-Analysis-macOS** — **ZIP** of the **Apple Silicon** `.app` (zip keeps the bundle intact when unzipping).
  - **McRoberts-Analysis-macOS-Intel** — **ZIP** of the **Intel (x86_64)** `.app` for older Macs.

**Note:** Workflow artifacts use GitHub’s **retention limit** (they expire after a set period).

### GitHub Releases (recommended for end users)

For **stable download links** that do not auto-expire like Actions artifacts, publish a **[GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)** and attach the same build outputs (Windows folder zipped if needed, macOS `.zip` of the `.app`). Point collaborators and manuals to the **Releases** page instead of asking them to dig through **Actions** history.

The CI jobs use **Python 3.11** and install PyInstaller plus the Python dependencies listed in that workflow file (they must stay in sync with what the GUI needs).

### Local build (developers)

From the **repository root**, using the same Python environment you use to run the GUI (with `oct2py`, `octave_kernel`, `ssqueezepy`, etc. installed):

```bash
python -m PyInstaller "McRoberts Analysis.spec" --clean
```

Use the **same interpreter** (venv or conda env) that can run `Main/GUI_Main.py`; the spec resolves package data from that environment.

### macOS notes

- CI produces **two** macOS bundles: **McRoberts-Analysis-macOS** (Apple Silicon, `macos-latest`) and **McRoberts-Analysis-macOS-Intel** (`macos-15-intel`). The workflow prints `uname -m` and `file` on the main binary so you can confirm `arm64` vs `x86_64`.
- If Gatekeeper blocks the app, use **System Settings → Privacy & Security** or right-click → Open, as usual for unsigned local builds.

## Program Instructions
    - Run GUI_Main and in the Select Data tab, add the desired OMX file
    - Zoom in and pan on the plot or manually type in the desired time range.
    - Once the desired time range is selected, hit export CSV to save the results in CSV format.
    - If you have just exported a file to CSV, it should be already loaded in the Mobilise-D and Ayush's Code tabs. If not or you wish to analyze a different file, you can do so manually.
    - In the Mobilise-D tab, after loading your file, select to use either the GSDA algorithm for healthy data or GSDB for patient data.
    - After selecting an algorithm, hit the run GSD detection button to run it. You can then save any or all of the data.
    - In the Ayush's code tab, after loading a file, you can run either linear analysis or nonlinear analysis, or both (note nonlinear analysis takes a long time.) It will then generate files and potentially multiple plots, which you can save with the various save buttons.

## Running analysis for large data in small samples
    - Sometimes the walking analysis will not work well for small segments (ex: 30s) of data, specifically if that data is stroke patient data.
    - To correct this and get more accurate data segments, you can cut say a day of data from the original OMX file, then run that day of data through the GSD algorithm. In console, the algorithm will print out a list of segments longer than 30s and will have better accuracy due to the larger range of data available. 
    - After getting this list, you can go back to the acceleration plot and zoom to one of those segments. Then you can export that and use it in further analysis. Because walking segmentation does not work as well with smaller segments of data, in the analysis tab you can check the box to assume data is walking, and the algorithm will skip the walking segmentation stage, processing all data as walking.

## Alex Lark Data Analysis method
    1. Upload large data file to 1st tab.
    2. After loading, adjust the end date of the plot to be exactly 24 hours after the start date, and export this 24-hour data.
    3. Once exported, switch to the 2nd tab and run the appropriate GSD algorithm on the 24-hour data. Ensure that force data as walking is unchecked. This step will take a while for the algorithm to run.
    4. Save all output. In console, you will see a list of all long segments greater than 30 seconds, their length, and their start and stop timestamps. Choose one of these long segments, switch back to to the first tab, and zoom in on that segment. 
    5. If the segment looks good, trim it to just 30 seconds. If it does not look good, select another long segment and try again. Once you are zoomed in on the 30 seconds, export that csv and plot.
    6. With your 30 seconds of data, run the GSD algorithm in tab 2, this time with force data as walking checked. Also run linear and nonlinear analysis in tab 3, with force data as walking also checked there. The nonlinear analysis may take some time. Once everything has run, save all output from both tabs 2 and 3. 
    7. Reset the plot in tab 1, then adjust the start date to move it forward by exactly 24 hours. Adjust the end date as well to move it forward by 24 hours. If the original data would not reach the new end date, leave the end date as it was originally. Once your bounds are set, this is your new 24-hour data. Export it. 
    8. Repeat steps 3 through 6. Repeat the process again so you have 3 whole days of data from the original dataset, as long as the data supports it. 

## Notes
    - All necessary files for GUI_Main are in Main, DynaportCompany_Codes_new, Mobilise-D-TVS-Recommended-Algorithms-master, or Non_GUI/Ayush_Files
    - By default, all results are stored in Data/Output in subfolders specifically created for the data