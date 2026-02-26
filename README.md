### Code under development for gridding XBT data and creating output files of the products


## Quick start (recommended)

1. Create and activate a virtual environment (Python 3.11+ recommended):

```
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies (pip):

```
pip install -r requirements.txt
```

Note: For scientific packages (netCDF4, xarray, numpy) using conda can simplify installation of compiled dependencies:

```
conda create -n xbt_env python=3.11 -c conda-forge
conda activate xbt_env
conda install -c conda-forge netcdf4 xarray numpy pandas scipy beautifulsoup4 requests
```

3. Run the transect gridding script:

```
python transect_vertical_grid.py <input_directory_or_url> <output_directory>
```

- `input_directory_or_url` may be a local folder containing `.nc` files or a THREDDS catalog URL.
- `output_directory` will receive the generated netCDF files.

## Notes for contributors and external users

- The repository includes a `requirements.txt` with conservative version bounds; for reproducible installs add a lockfile for your package manager.
- If you use PyCharm or another IDE and it cannot find local modules (e.g., `interp_gaussian.py`), mark the project folder as a Sources Root or ensure the interpreter's working directory includes the project root.
- The code includes defensive checks for empty inputs; if you see runtime errors when processing a dataset, please open an issue with a small reproducible example.

## MATLAB usage

The repository includes MATLAB utilities under `matlab/` for spatial gridding. To set system paths, the MATLAB scripts look for data and bathymetry files using the following strategy (in order):

- Environment variables: `XBT_DATA_DIR` (top-level data folder) and `XBT_OUT_DIR` (top-level output folder).
- Repo-relative candidate: `$(repo_root)/data/...` and `$(repo_root)/output/...`.
- For GEBCO bathymetry the `GEBCO_PATH` environment variable can point directly to the GEBCO netCDF file.

Examples (bash / zsh):

```bash
# set env vars to point to your local data locations
export XBT_DATA_DIR=/path/to/my/xbt_data
export XBT_OUT_DIR=/path/to/where/i/want/output
export GEBCO_PATH=/path/to/gebco_30sec.nc

# Run the main matlab control script from MATLAB command line or script
# In MATLAB:
% cd('matlab');
% run('grid_control.m');
```

If you prefer, place required files under `data/` in the repository root using the same structure expected by the scripts (e.g. `data/PX34_32/transect_files/` and `data/bath/gebco08_30sec.nc`).