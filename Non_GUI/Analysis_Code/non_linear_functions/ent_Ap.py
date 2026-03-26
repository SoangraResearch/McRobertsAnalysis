import numpy as np
from scipy.spatial import cKDTree

def Ent_Ap(data, dim, r):
    """
    Ent_Ap20120321
      data : time-series data
      dim : embedded dimension
      r : tolerance (typically 0.2)
    
      Changes in version 1
          Ver 0 had a minor error in the final step of calculating ApEn
          because it took logarithm after summation of phi's.
          In Ver 1, I restored the definition according to original paper's
          definition, to be consistent with most of the work in the
          literature. Note that this definition won't work for Sample
          Entropy which doesn't count self-matching case, because the count 
          can be zero and logarithm can fail.
    
      *NOTE: This code is faster and gives the same result as ApEn = 
             ApEnt(data,m,R) created by John McCamley in June of 2015.
             -Will Denton
    
    ---------------------------------------------------------------------
    coded by Kijoon Lee,  kjlee@ntu.edu.sg
    Ver 0 : Aug 4th, 2011
    Ver 1 : Mar 21st, 2012
    ---------------------------------------------------------------------
    May 2023 - Updated for addition in Nonlinear Analysis Toolkit by
               Shifat Sarwar, ssarwar@unomaha.edu
    ---------------------------------------------------------------------
    """


    data = np.asarray(data, dtype=float).reshape(-1)
    r = r * np.std(data)
    N = len(data)
    phim = np.zeros(2, dtype=float)

    for j in range(2):
        m = dim + j
        n = N - m + 1
        if n <= 0:
            raise ValueError("Embedding dimension is too large for input length.")

        data_mat = np.lib.stride_tricks.sliding_window_view(data, m)
        tree = cKDTree(data_mat)

        # Match original behavior exactly: include self-matches and use <= r
        # Count neighbors without materializing full index lists (prevents OOM on long bouts).
        counts = tree.query_ball_point(data_mat, r=r, p=np.inf, return_length=True)
        phi = counts.astype(float) / n
        phim[j] = np.sum(np.log(phi)) / n

    AE = phim[0] - phim[1]
    return AE