import numpy as np
from scipy.spatial import cKDTree

def Ent_MS_Plus(x, tau, m, r, compute_gmse_msfe=True):
    """
    compute_gmse_msfe: If False, skip GMSE and MSFE (fuzzy entropy), which are
    not used by Tab3 but cost O(N^2) per scale. Default True preserves full
    outputs for scripts/notebooks; the GUI passes False for speed.
    """

    R = r*np.std(x)
    N = len(x)

    GMSE = np.zeros(tau, dtype=object)
    MSE = np.zeros(tau, dtype=object)
    MSFE = np.zeros(tau, dtype=object)
    CMSE = np.zeros(tau, dtype=object)
    RCMSE = np.zeros(tau, dtype=object)

    for i in range(1,tau):
        Ndivi = int(N/i) # defining this now because we use it a lot later on.
        if compute_gmse_msfe:
            o2 = np.zeros((i, Ndivi))
            for j in range(Ndivi):
                for k in range(i):
                    try:
                        o2[k,j] = np.var(x[(j-1)*i+k:j*i+k])
                    except:
                        o2[k,j] = np.nan
            GMSE[i] = Samp_Ent(o2[0,:], m, r)
        else:
            GMSE[i] = np.nan

        # Coarse-graining for MSE and derivatives
        y_tau_kj = np.zeros((i,Ndivi))
        for j in range(Ndivi):
            for k in range(i):
                try:
                    y_tau_kj[k,j] = 1/i*np.sum(x[(j-1)*i+k:j*i+k])
                except:
                    y_tau_kj[k,j] = np.nan
        
        valid_indices = ~np.isnan(y_tau_kj[0, :])
        # Multiscale Entropy (MSE)
        MSE[i] = Samp_Ent(y_tau_kj[0, valid_indices], m, R)        
        #Multiscale Fuzzy Entropy (MFE)
        if compute_gmse_msfe:
            MSFE[i] = Fuzzy_Ent(y_tau_kj[0, valid_indices], m, R, 2)
        else:
            MSFE[i] = np.nan
        
        # Composite Multiscale Entropy (CMSE)
        CMSE[i] = 0

        nm = np.zeros(i)
        nm1 = np.zeros(i)
        for k in range(i):
            valid_indices_k = ~np.isnan(y_tau_kj[k, :])
            _, nm[k], nm1[k] = Samp_Ent(y_tau_kj[k, valid_indices_k], m, R)
            CMSE[i] += (1 / i) * -np.log(nm1[k] / nm[k])

        n_m1_ktau = np.mean(nm1)
        n_m_ktau = np.mean(nm)
        RCMSE[i] = -np.log(n_m1_ktau / n_m_ktau)


    return RCMSE, CMSE, MSE, MSFE, GMSE

def Samp_Ent(data, m, r):
    """
    [SE,sum_nm,sum_nm1] = Samp_Ent(data,m,r)
    This is a faster version of the previous code - Samp_En.m

    inputs     - data, single column time seres
               - m, length of vectors to be compared
               - R, radius for accepting matches (as a proportion of the
                    standard deviation)

    output     - SE, sample entropy
               - sum_nm, total number of matches for vector length m
               - sum_nm1, total number of matches for vector length m+1
    
    Remarks
    This code finds the sample entropy of a data series using the method
    described by - Richman, J.S., Moorman, J.R., 2000. "Physiological
    time-series analysis using approximate entropy and sample entropy."
    Am. J. Physiol. Heart Circ. Physiol. 278, H2039–H2049.


    J McCamley May, 2016
    W Denton August, 2017 (Made count total number of matches for each vector length, necessary for CMSE and RCMSE)
    """

    data = np.asarray(data, dtype=float).reshape(-1)
    data = data[~np.isnan(data)]
    N = len(data)
    if N == 0:
        return (np.nan, 0.0, 0.0)

    R = r * np.std(data)
    n = N - m
    if n <= 0:
        return (np.nan, 0.0, 0.0)

    emb_m = np.lib.stride_tricks.sliding_window_view(data, m)[:n]
    emb_m1 = np.lib.stride_tricks.sliding_window_view(data, m + 1)[:n]

    tree_m = cKDTree(emb_m)
    tree_m1 = cKDTree(emb_m1)
    counts_m = tree_m.query_ball_point(emb_m, r=R, p=np.inf, return_length=True)
    counts_m1 = tree_m1.query_ball_point(emb_m1, r=R, p=np.inf, return_length=True)

    Bm = counts_m.astype(float) / n
    Am = counts_m1.astype(float) / n
    Bmr = np.sum(Bm) / n
    Amr = np.sum(Am) / n

    sum_nm = float(np.sum(counts_m))
    sum_nm1 = float(np.sum(counts_m1))

    if Bmr <= 0 or Amr <= 0 or Amr / Bmr <= 0:
        return (np.nan, sum_nm, sum_nm1)
    return (-np.log(Amr / Bmr), sum_nm, sum_nm1)

def Fuzzy_Ent(series, dim, r, n):
    N = len(series)
    phi = np.zeros(2)
    r = r * np.std(series)

    for j in range(2):
        m = dim + j - 1
        if m == 1:
            patterns = series.reshape(1, -1)
        else:
            patterns = np.zeros((m, N - m + 1))
            for i in range(m):
                patterns[i, :] = series[i:N - m + i + 1]
        
        for i in range(N - m + 1):
            patterns[:, i] -= np.mean(patterns[:, i])
        
        aux = np.zeros(N - m + 1)
        for i in range(N - m + 1):
            if m == 1:
                dist = np.abs(patterns - patterns[:, i].reshape(-1, 1))
            else:
                dist = np.max(np.abs(patterns - patterns[:, i].reshape(-1, 1)), axis=0)
            
            simi = np.exp(-dist**n / r)
            aux[i] = (np.sum(simi) - 1) / (N - m)
        
        phi[j] = np.sum(aux) / (N - m + 1)

    fuzzy_ent = np.log(phi[0]) - np.log(phi[1])
    #print(f"Fuzzy_Ent: {fuzzy_ent}, phi[0]: {phi[0]}, phi[1]: {phi[1]}")
    return fuzzy_ent