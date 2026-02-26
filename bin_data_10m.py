import numpy as np

def bin_data_10m(depths, temperatures):
    """
    Bin temperature data into 10 meter vertical intervals.

    Parameters:
    depths (np.ndarray): 1D array of depth measurements (in meters).
    temperatures (np.ndarray): 1D array of temperature measurements corresponding to the depths.

    Returns:
    binned_depths (np.ndarray): 1D array of binned depth intervals (center of each bin).
    binned_temperatures (np.ndarray): 1D array of average temperatures for each bin.
    """
    # Define bin edges from the minimum to maximum depth in 10 meter intervals
    min_depth = np.floor(np.min(depths) / 10) * 10
    max_depth = np.ceil(np.max(depths) / 10) * 10
    bin_edges = np.arange(min_depth, max_depth + 10, 10)

    # Initialize arrays to hold binned depths and temperatures
    binned_depths = []
    binned_temperatures = []

    # Bin the data
    for i in range(len(bin_edges) - 1):
        bin_mask = (depths >= bin_edges[i]) & (depths < bin_edges[i + 1])
        if np.any(bin_mask):
            binned_depths.append((bin_edges[i] + bin_edges[i + 1]) / 2)
            binned_temperatures.append(np.mean(temperatures[bin_mask]))

    return np.array(binned_depths), np.array(binned_temperatures)


# Example usage
if __name__ == "__main__":
    depths = np.array([5, 15, 25, 35, 45, 55, 65, 75, 85, 95])
    temperatures = np.array([10, 12, 14, 13, 15, 16, 14, 13, 12, 11])
    binned_depths, binned_temperatures = bin_data_10m(depths, temperatures)
    print("Binned Depths:", binned_depths)
    print("Binned Temperatures:", binned_temperatures)
