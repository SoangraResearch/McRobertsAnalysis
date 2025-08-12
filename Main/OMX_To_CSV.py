import sys
import os
import atexit
import time
import numpy as np
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