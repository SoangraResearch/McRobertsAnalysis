import pandas as pd

def split_data_by_day(data, timestamps):
    chunks = []
    current_chunk_indices = []
    start_timestamp = timestamps[0]
    current_day_end = start_timestamp + 1.0

    for i, ts in enumerate(timestamps):
        current_chunk_indices.append(i)

        if i == len(timestamps) - 1 or timestamps[i + 1] >= current_day_end:
            print(data["ACC"])
            chunk_data = pd.DataFrame(data["ACC"], columns=["Time", "X", "Y", "Z"]).iloc[current_chunk_indices]
            chunks.append(chunk_data)
            current_chunk_indices = []
            current_day_end += 1.0
    
    #add chunks less than 24h
    if current_chunk_indices:
        chunk_data = data["ACC"][current_chunk_indices]
        chunks.append(chunk_data)

    return chunks

    
