# grid temperature data vertically using Gaussian interpolation
import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d

def vinterp_gauss_simple(depths, data, v_grid, half_width=11):
    """
    Simplified vertical smoothing using scipy's gaussian_filter1d

    Works best when depths are regularly spaced.
    """
    depths = np.asarray(depths).flatten()
    data = np.asarray(data).flatten()
    v_grid = np.asarray(v_grid).flatten()

    # Remove NaNs and sort
    valid = ~(np.isnan(depths) | np.isnan(data))
    if np.sum(valid) < 5:
        return np.full(len(v_grid), np.nan)

    depths = depths[valid]
    data = data[valid]
    sort_idx = np.argsort(depths)
    depths = depths[sort_idx]
    data = data[sort_idx]

    # Estimate grid spacing
    dd = np.median(np.diff(depths))

    # Convert half_width to samples
    sigma = half_width / dd

    # Apply Gaussian filter
    data_smooth = gaussian_filter1d(data, sigma=sigma, mode='nearest')

    # Interpolate to target grid
    interp_func = interp1d(depths, data_smooth, kind='linear',
                           bounds_error=False, fill_value=np.nan)
    zsmooth = interp_func(v_grid)

    # if there is Nan in the first to second element and length of v_grid >2
    # count non-NaN values in zsmooth and then fill first two entries if needed
    n_non_nan = np.count_nonzero(~np.isnan(zsmooth))
    if n_non_nan > 2:
        if np.isnan(zsmooth[0]):
            # get the mean of the data less than or equal to 10m depth
            mean_shallow = np.nanmean(data[depths <= 10])
            zsmooth[0] = mean_shallow
        if np.isnan(zsmooth[1]):
            # if zsmooth[0] is still Nan, fill it with mean of data less than or equal to 20m depth
            if np.isnan(zsmooth[0]):
                # get the mean of the data less than or equal to 20m depth
                mean_shallow = np.nanmean(data[depths <= 20])
                zsmooth[0] = mean_shallow
                zsmooth[1] = mean_shallow
            else:
                # get the mean of data > 10m and less than or equal to 20m depth
                mean_shallow = np.nanmean(data[(depths > 10) & (depths <= 20)])
                zsmooth[1] = mean_shallow


    return zsmooth