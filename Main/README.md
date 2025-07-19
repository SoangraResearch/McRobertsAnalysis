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
    In Powershell, run: setx OCTAVE_EXECUTABLE "C:\Program Files\GNU Octave\Octave-10.2 0\mingw64\bin\octave-cli.exe" (or alternative installation path)

- On **macOS**
    In Terminal, run: export OCTAVE_EXECUTABLE=$(which octave-cli)
    This sets the path temporarily.
    To set it permanently, add the same line to your shell config file (e.g. ~/.zshrc or ~/.bash_profile):

## Program Instructions
    - 