import numpy as np
from scipy.spatial import cKDTree

def Ent_Samp(data, m, r):
  """
  function SE = Ent_Samp20200723(data,m,r)
  SE = Ent_Samp20200723(data,m,R) Returns the sample entropy value.
  inputs - data, single column time seres
          - m, length of vectors to be compared
          - r, radius for accepting matches (as a proportion of the
            standard deviation)
  output - SE, sample entropy
  Remarks
  - This code finds the sample entropy of a data series using the method
    described by - Richman, J.S., Moorman, J.R., 2000. "Physiological
    time-series analysis using approximate entropy and sample entropy."
    Am. J. Physiol. Heart Circ. Physiol. 278, H2039–H2049.
  - m is generally recommendation as 2
  - R is generally recommendation as 0.2
  May 2016 - Modified by John McCamley, unonbcf@unomaha.edu
           - This is a faster version of the previous code.
  May 2019 - Modified by Will Denton
           - Added code to check version number in relation to a server
             and to automatically update the code.
  Jul 2020 - Modified by Ben Senderling, bmchnonan@unomaha.edu
           - Removed the code that automatically checks for updates and
             keeps a version history.
  May 2023 - Updated for addition in Nonlinear Analysis Toolkit by
             Shifat Sarwar, ssarwar@unomaha.edu
  Define r as R times the standard deviation
  """
  data = np.asarray(data, dtype=float).reshape(-1)
  R = r * np.std(data)
  N = len(data)
  n = N - m
  if n <= 0:
    raise ValueError("Embedding dimension is too large for input length.")

  # Preserve historical implementation behavior: it uses N-m templates.
  emb_m = np.lib.stride_tricks.sliding_window_view(data, m)[:n]
  emb_m1 = np.lib.stride_tricks.sliding_window_view(data, m + 1)[:n]

  tree_m = cKDTree(emb_m)
  tree_m1 = cKDTree(emb_m1)

  # Use count-only mode to avoid allocating neighbor index lists for every point.
  counts_m = tree_m.query_ball_point(emb_m, r=R, p=np.inf, return_length=True)
  counts_m1 = tree_m1.query_ball_point(emb_m1, r=R, p=np.inf, return_length=True)

  # Match original self-match handling exactly.
  Bm = (counts_m.astype(float) - 1.0) / n
  Am = (counts_m1.astype(float) - 1.0) / n

  Bmr = np.mean(Bm)
  Amr = np.mean(Am)

  return -np.log(Amr / Bmr)