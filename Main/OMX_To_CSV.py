import sys
import os
import atexit
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from datetime import datetime, timedelta
from oct2py import Oct2Py

def process_omx_file(filepath: str):
    
    #setting working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    #Initializing Oct2Py
    oc = Oct2Py()
    atexit.register(oc.exit)

    #Adding necessary filepath
    oc.addpath('../DynaportCompany_Codes_new/source')

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
    print("Reading acceleration data...")
    tic = time.perf_counter()
    data = oc.feval(
        'OMX_readFile',
        filepath,
        0,                        # info
        info.packetInfo,         # packetInfo
        -1,                      # startTime
        -1,                      # stopTime
        0,                       # verbose
        0,                       # useC
        [1, 1, 0],               # modality
        1,                       # step
        nout=1,
        struct_to_dict=False
    )
    toc = time.perf_counter()
    print(f"Read data in {toc - tic:0.4f} seconds")
    return data

#data = process_omx_file(r"C:\Users\ahala\OneDrive\Desktop\SoangraResearch\McRobertsAnalysis\Data\OMX_Files\TestData.OMX")

#Plotting the data
#x = data['ACC'][:, 0]
#y_columns = data['ACC'][:, 1:4]

#plt.figure(figsize=(10, 6))
#plt.plot(x, y_columns)
#plt.title('Plot of data1 ACC')
#plt.xlabel('Index')
#plt.ylabel('Value')
#plt.show()

#TODO: convert to CSV