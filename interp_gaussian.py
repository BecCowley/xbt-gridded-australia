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

    return zsmooth