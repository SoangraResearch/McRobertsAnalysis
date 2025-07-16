import os
import h5py
import pandas as pd
from datetime import datetime, timedelta

# Helper function
def matlab_datenum_to_datetime(datenum):
    days = int(datenum)
    frac = datenum % 1
    return datetime.fromordinal(days - 366) + timedelta(days=frac)

# Load H5 file and extract time
def load_h5_file(file_path):
    with h5py.File(file_path, "r") as f:
        dataset = list(f.values())[0][()]
        time_row = dataset[0, :]
        time_array = [matlab_datenum_to_datetime(t) for t in time_row]
    return dataset, time_array

# Save DataFrame to file
def save_dataframe(df, output_path, format='CSV'):
    try:
        if format.upper() == 'CSV':
            df.to_csv(output_path, index=False)
        elif format.upper() == 'JSON':
            df.to_json(output_path, orient='records', lines=True)
        print(f"Data exported to: {output_path}")
    except Exception as e:
        print(f"Failed to save file: {str(e)}")

# Main export function
def export_data(file_path, start_time_str, stop_time_str, output_path, format='CSV'):
    dataset, time_array = load_h5_file(file_path)

    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    stop_time = datetime.strptime(stop_time_str, "%Y-%m-%d %H:%M:%S")

    indices = [i for i, t in enumerate(time_array) if start_time <= t <= stop_time]
    if not indices:
        print("⚠️ No data found in the selected time range.")
        return

    extracted = pd.DataFrame(dataset[:, indices]).iloc[0:4]
    df = extracted.T
    df.columns = ['Time', 'Ax', 'Ay', 'Az']

    # Show first few rows in notebook
    print (df.head()) # FOR: .py files
    #display(df.head()) #FOR: .ipynb files

    save_dataframe(df, output_path, format=format)

# ====== JUPYTER CELL CONFIG ======
# Set your variables here:
file_path = "C:/Users/ahala/OneDrive/Desktop/SoangraResearch/McRobertsAnalysis/Data/H5_Files/TestData.h5"  # <-- set your .h5 file path # TODO: use relative filepath
output_path = "C:/Users/ahala/OneDrive/Desktop/SoangraResearch/McRobertsAnalysis/Data/CSV_Files_Raw/TestData.csv"  # <-- set your desired output file name # TODO: use relative filepath

# After loading, we’ll show the available time range
dataset, time_array = load_h5_file(file_path)
file_start_time = time_array[0].strftime("%Y-%m-%d %H:%M:%S")
file_stop_time = time_array[-1].strftime("%Y-%m-%d %H:%M:%S")

print(f"File Start Time: {file_start_time}")
print(f"File Stop Time: {file_stop_time}")

# Set desired time window (use file_start_time/file_stop_time if you want full range)
start_time_str = file_start_time
stop_time_str = file_stop_time

# Choose format ('CSV' or 'JSON')
export_format = 'CSV'

# ====== RUN EXPORT ======
export_data(file_path, start_time_str, stop_time_str, output_path, format=export_format)
