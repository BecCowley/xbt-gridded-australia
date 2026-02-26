# read in all netcdf files in the XBT transect, extract TEMP, DEPTH, LAT, LON, TIME, SOOP_line information.
# remove any bad data where TEMP_quality_control != 1, 2 or 5
# bin the data to 10 m vertical intervals using the bin_data_10m function from bin_data_10m.py
# output a single netcdf file with the cleaned and binned data, including the following variables:
# DEPTH (binned depth intervals), TEMP (binned temperatures), LAT, LON, TIME, SOOP_line
# include appropriate attributes for each variable and for the global file

import os
import sys
import numpy as np
import xarray as xr
import pandas as pd
from write2netcdf import write_vert_grid_nc
import requests
from bs4 import BeautifulSoup
from interp_gaussian import vinterp_gauss_simple
from utils import make_transect_id
# Import for parallel processing
from concurrent.futures import ThreadPoolExecutor, as_completed


# Extract file processing into separate function for parallelization
def process_single_file(filepath, v_grid):
    """Process a single netCDF file and return extracted data"""
    try:
        ds = xr.open_dataset(filepath)

        # Extract variables
        depths = ds['DEPTH'].values
        temperatures = ds['TEMP'].values.flatten()
        temp_quality_control = ds['TEMP_quality_control'].values.flatten()
        lat = np.asarray(ds['LATITUDE'].values).squeeze().item()
        lon = np.asarray(ds['LONGITUDE'].values).squeeze().item()
        time = np.asarray(ds['TIME'].values).squeeze().item()

        if 'XBT_uniqueid' in ds.attrs:
            station_number = ds.attrs.get('XBT_uniqueid', 'Unknown')
        else:
            station_number = ds['Institution_unique_identifier'].values.item().decode('utf-8')

        # SOOP_line could be 'XBT_line' in global attributes or in SOOP_line variable attributes
        if 'XBT_line' in ds.attrs:
            soop_line = ds.attrs.get('XBT_line', 'Unknown')
            soop_line_description = ds.attrs.get('XBT_line_description', 'No description available')
        else:
            soop_line = ds['SOOP_line'].attrs.get('SOOP_line_label', 'Unknown')
            soop_line_description = ds['SOOP_line'].attrs.get('SOOP_line_description', 'No description available')

        # Cruise_ID could be in Ship attributes or global attributes as 'XBT_cruise_id'
        if 'XBT_cruise_ID' in ds.attrs:
            cruise_id = ds.attrs.get('XBT_cruise_ID', 'Unknown')
        else:
            cruise_id = ds['Ship'].attrs.get('Cruise_ID', 'Unknown')

        # Remove bad data where TEMP_quality_control is not 0, 1, 2, or 5 and where temperatures are less than -5 or greater than 40
        valid_mask = np.isin(temp_quality_control, [0, 1, 2, 5]) & (temperatures >= -5) & (temperatures <= 40)
        depths = depths[valid_mask]
        temperatures = temperatures[valid_mask]

        # if there is no valid data, return None
        if len(temperatures) == 0:
            print('No valid temperature data in file: %s' % filepath)
            return None

        # return interpolated gaussian smoothed data on with 10m intervals from 0 to 1800m
        interp_temps = vinterp_gauss_simple(depths, temperatures, v_grid, half_width=11)

        # Return structured data instead of appending to lists
        return {
            'depths': v_grid.copy(),
            'temps': interp_temps,
            'lat': lat,
            'lon': lon,
            'time': time,
            'soop_line': soop_line,
            'soop_line_description': soop_line_description,
            'cruise_id': cruise_id,
            'station_number': station_number
        }
    except Exception as e:
        print(f'Error processing file {filepath}: {e}')
        return None


def clean_and_bin_transect(input_directories, output_directory):
    # Pre-define v_grid outside of loop for reuse
    max_depth = 1800
    v_grid = np.arange(0, max_depth + 10, 10)

    # Check if input_directory is a URL (THREDDS) or local path
    is_url = input_directories[0].startswith('http://') or input_directories[0].startswith('https://')

    # check if this is a url or a local directory
    if is_url:
        file_urls = []
        # cycle over the list of input directories
        for input_directory in input_directories:
            # if url, download all netcdf files to a temporary directory
            response = requests.get(input_directory)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a')
            for link in links:
                href = link.get('href')
                if href and href.endswith('.nc') and 'TEST' not in href:
                    # remove the ''catalog.html?dataset=' part if it exists
                    if 'catalog.html?dataset=' in href:
                        href = href.split('catalog.html?dataset=')[-1]
                    # construct the full file url
                    file_url = input_directory.rsplit('/', 1)[0] + '/' + href.rsplit('/', 1)[-1]
                    # replace '/catalog/' with '/dodsC/' to get the direct access url
                    file_url = file_url.replace('/catalog/', '/dodsC/').replace('.html', '')
                    file_urls.append(file_url)
        filenames = file_urls
    else:
        # Loop through all netCDF files in the input directory where name does not contain 'TEST' and ends with .nc
        filenames = [f for f in os.listdir(input_directories[0]) if f.endswith('.nc') and 'TEST' not in f]
    # sort filenames alphabetically
    filenames.sort()

    # Parallel file processing with ThreadPoolExecutor
    print(f"Processing {len(filenames)} files in parallel...")
    file_results = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all file processing tasks
        future_to_file = {
            executor.submit(process_single_file,
                            filename if is_url else os.path.join(input_directories[0], filename),
                            v_grid): filename
            for filename in filenames
        }

        # Collect results as they complete
        for future in as_completed(future_to_file):
            result = future.result()
            if result is not None:
                file_results.append(result)

    print(f"Successfully processed {len(file_results)} files")

    # Build DataFrame from records more efficiently
    records = []
    for result in file_results:
        n_depths = len(result['depths'])
        for i in range(n_depths):
            records.append({
                'DEPTH': result['depths'][i],
                'TEMP': result['temps'][i],
                'LATITUDE': result['lat'],
                'LONGITUDE': result['lon'],
                'TIME': result['time'],
                'SOOP_line': result['soop_line'],
                'SOOP_line_description': result['soop_line_description'],
                'Cruise_ID': result['cruise_id'],
                'Institution_unique_identifier': result['station_number']
            })

    df = pd.DataFrame.from_records(records)

    # Convert TIME to datetime once - major performance improvement
    df['TIME'] = pd.to_datetime(df['TIME'])

    # Use categorical dtype for repeated strings - reduces memory and speeds up operations
    df['SOOP_line'] = df['SOOP_line'].astype('category')
    df['SOOP_line_description'] = df['SOOP_line_description'].astype('category')
    df['Cruise_ID'] = df['Cruise_ID'].astype('category')

    # sort df by TIME and DEPTH and reset index
    df = df.sort_values(by=['TIME', 'DEPTH']).reset_index(drop=True)

    # add a 'transect_id' column to df initialized to empty strings
    df['transect_id'] = ''

    # Initialize set once and update incrementally
    existing_transect_ids = set()

    # do an initial separation of transects based on Cruise_ID
    unique_cruise_ids = df['Cruise_ID'].unique()
    for cruise_id in unique_cruise_ids:
        cruise_mask = df['Cruise_ID'] == cruise_id
        cruise_df = df.loc[cruise_mask]
        soop_line = cruise_df['SOOP_line'].iloc[0]
        # No need to convert TIME again, already datetime
        unique_dates = np.sort(cruise_df['TIME'].unique())
        if unique_dates.size == 0:
            continue
        # ensure that the total cruise does not cover more than 20 days
        if max(unique_dates) - min(unique_dates) > pd.Timedelta(days=20):
            # separate where the date changes by more than 5 days
            date_diffs = np.diff(unique_dates)
            gap_indices = np.where(date_diffs > pd.Timedelta(days=10))[0]
            sub_dates = []
            sub_dates_end = []
            if len(gap_indices) > 0:
                for i in range(len(gap_indices)):
                    if i == 0:
                        sub_dates = unique_dates[:gap_indices[i] + 1]
                    else:
                        sub_dates = unique_dates[gap_indices[i - 1] + 1:gap_indices[i] + 1]
                    # if this is the last gap, include all remaining dates
                    if i == len(gap_indices) - 1:
                        sub_dates_end = unique_dates[gap_indices[i] + 1:]
                    else:
                        # leave sub_dates_end as an empty list until possibly overwritten
                        pass
                    # Use and update existing_transect_ids set
                    transect_id = make_transect_id(soop_line, sub_dates[0], existing_transect_ids)
                    existing_transect_ids.add(transect_id)
                    # No need to convert TIME, use direct comparison
                    sub_cruise_mask = cruise_mask & df['TIME'].isin(sub_dates)
                    df.loc[sub_cruise_mask, 'transect_id'] = transect_id
                # handle the last segment after the last gap
                if len(sub_dates_end) > 0:
                    # Use and update existing_transect_ids set
                    transect_id = make_transect_id(soop_line, sub_dates_end[0], existing_transect_ids)
                    existing_transect_ids.add(transect_id)
                    # No need to convert TIME
                    sub_cruise_mask = cruise_mask & df['TIME'].isin(sub_dates_end)
                    df.loc[sub_cruise_mask, 'transect_id'] = transect_id
                continue
        if len(unique_dates) == 0:
            continue
        # Use and update existing_transect_ids set
        transect_id = make_transect_id(soop_line, unique_dates[0], existing_transect_ids)
        existing_transect_ids.add(transect_id)
        df.loc[cruise_mask, 'transect_id'] = transect_id

    # re-calculate unique transects
    unique_transects = df['transect_id'].unique()

    # Cache transect dataframes to avoid repeated filtering
    print("Caching transect dataframes...")
    transect_dfs = {transect: df[df['transect_id'] == transect].copy()
                    for transect in unique_transects}

    # review each transect, checking for change in direction of lat or lon
    for transect in unique_transects:
        # Use cached dataframe
        transect_df = transect_dfs[transect]
        transect_mask = df['transect_id'] == transect

        # get unique latitudes and longitudes in order of time
        unique_lats = transect_df[['TIME', 'LATITUDE']].drop_duplicates()
        unique_lons = transect_df[['TIME', 'LONGITUDE']].drop_duplicates()

        # work on only lat or lon, whichever has the larger range
        lat_diff = np.diff(unique_lats['LATITUDE'].values)
        lon_diff = np.diff(unique_lons['LONGITUDE'].values)
        # Use numpy ptp (peak-to-peak) for cleaner range calculation
        lat_range = np.ptp(unique_lats['LATITUDE'].values)
        lon_range = np.ptp(unique_lons['LONGITUDE'].values)

        if lat_range >= lon_range:
            # compute sign, treat zeros as NaN, forward/back-fill to propagate nearest non-zero sign
            s = np.sign(lat_diff).astype(float)
        else:
            s = np.sign(lon_diff).astype(float)

        # set zeros to NaN
        s[s == 0] = np.nan
        s = pd.Series(s).ffill().bfill().values

        # where there are single positive or negative values surrounded by opposite sign, set to NaN
        s = pd.Series(s)
        # mask single-element spikes: neighbors equal and center is different (and none are NaN)
        spike_mask = (
                s.notna()
                & s.shift(1).notna()
                & s.shift(-1).notna()
                & (s.shift(1) == s.shift(-1))
                & (s != s.shift(1))
        )
        s[spike_mask] = np.nan
        s = pd.Series(s).ffill().bfill().values

        # change values at ends of s if they are different from their only neighbor
        if len(s) > 1:
            if s[0] != s[1]:
                s[0] = s[1]
            if s[-1] != s[-2]:
                s[-1] = s[-2]

        # indices where sign changes between consecutive (non-zero) differences
        direction_changes = np.where(np.diff(s) != 0)[0]
        if len(direction_changes) > 0:
            # if there are direction changes, split the transect at each change
            for direction in direction_changes:
                # if the percentage of direction changes to total points is > 0.5, then ignore direction changes
                if (len(s) - direction) / len(s) > 0.75:
                    print('Ignoring direction changes for transect: %s due to high frequency of changes' % transect)
                    break
                change_index = direction + 1  # +1 to get the index after the change
                change_time = unique_lats['TIME'].values[change_index]
                # Use the SOOP_line from the transect_df to ensure variable is available in this scope
                soop_line_local = transect_df['SOOP_line'].iloc[0] if 'SOOP_line' in transect_df.columns else transect.split('-')[0]
                # Use and update existing_transect_ids set
                new_transect_id = make_transect_id(soop_line_local, change_time, existing_transect_ids)
                existing_transect_ids.add(new_transect_id)
                df.loc[transect_mask & (df['TIME'] >= change_time), 'transect_id'] = new_transect_id

    # Update transect_dfs cache after splitting
    unique_transects = df['transect_id'].unique()
    transect_dfs = {transect: df[df['transect_id'] == transect].copy()
                    for transect in unique_transects}

    # Build transect_info using groupby for better performance
    print("Building transect info...")
    transect_summary = df.groupby('transect_id').agg({
        'TIME': ['min', 'max'],
        'LATITUDE': ['min', 'max', 'first', 'last'],
        'LONGITUDE': ['min', 'max', 'first', 'last']
    })

    transect_info = {}
    for transect in unique_transects:
        summary = transect_summary.loc[transect]
        time_min = summary[('TIME', 'min')]
        time_max = summary[('TIME', 'max')]
        lat_range = summary[('LATITUDE', 'max')] - summary[('LATITUDE', 'min')]
        lon_range = summary[('LONGITUDE', 'max')] - summary[('LONGITUDE', 'min')]

        # assign direction based on overall change in lat or lon
        if lat_range >= lon_range:
            if summary[('LATITUDE', 'last')] - summary[('LATITUDE', 'first')] > 0:
                direction = 'N'
            else:
                direction = 'S'
        else:
            if summary[('LONGITUDE', 'last')] - summary[('LONGITUDE', 'first')] > 0:
                direction = 'E'
            else:
                direction = 'W'

        # assign information to transect_info dictionary
        transect_info[transect] = {
            'start_time': time_min,
            'end_time': time_max,
            'duration_days': time_max - time_min,
            'direction': direction
        }

    # now combine transects with same direction and combined duration < 15 days
    print("Combining transects...")
    processed_transects = set()
    for transect_a in unique_transects:
        if transect_a in processed_transects:
            continue
        info_a = transect_info[transect_a]
        combined_transect = [transect_a]
        for transect_b in unique_transects:
            if transect_b == transect_a or transect_b in processed_transects:
                continue
            info_b = transect_info[transect_b]
            if info_a['direction'] == info_b['direction']:
                combined_duration = (max(info_a['end_time'], info_b['end_time']) - min(info_a['start_time'],
                                                                                       info_b['start_time'])).days

                # Use cached dataframes
                transect_a_df = transect_dfs[transect_a].sort_values(by='TIME')
                transect_b_df = transect_dfs[transect_b].sort_values(by='TIME')

                combined_lats = pd.concat(
                    [transect_a_df[['TIME', 'LATITUDE']], transect_b_df[['TIME', 'LATITUDE']]]).sort_values(by='TIME')
                combined_lons = pd.concat(
                    [transect_a_df[['TIME', 'LONGITUDE']], transect_b_df[['TIME', 'LONGITUDE']]]).sort_values(by='TIME')
                lat_monotonic = combined_lats['LATITUDE'].is_monotonic_increasing or combined_lats[
                    'LATITUDE'].is_monotonic_decreasing
                lon_monotonic = combined_lons['LONGITUDE'].is_monotonic_increasing or combined_lons[
                    'LONGITUDE'].is_monotonic_decreasing

                if not lat_monotonic and not lon_monotonic:
                    continue
                if combined_duration < 15:
                    combined_transect.append(transect_b)
                    processed_transects.add(transect_b)
                    # update info_a to reflect the combined transect
                    info_a['start_time'] = min(info_a['start_time'], info_b['start_time'])
                    info_a['end_time'] = max(info_a['end_time'], info_b['end_time'])
                    info_a['duration_days'] = combined_duration

        if len(combined_transect) > 1:
            new_transect_id = combined_transect[0]
            for t in combined_transect:
                df.loc[df['transect_id'] == t, 'transect_id'] = new_transect_id
            processed_transects.add(transect_a)

    unique_transects = df['transect_id'].unique()

    # for each unique transect, write out the data to a netcdf file
    print(f"Writing {len(unique_transects)} transects to netCDF files...")
    for transect in unique_transects:
        transect_mask = df['transect_id'] == transect

        # create a matrix of DEPTH vs TEMP for that transect where rows are DEPTH and columns are station numbers
        # Avoid redundant sorting and filtering
        transect_df = df.loc[transect_mask].sort_values(by=['TIME', 'DEPTH'])
        pivot_df = transect_df.pivot_table(index='DEPTH', columns='TIME', values='TEMP')
        # keep entire grid of DEPTH from 0 to 1800m in 10m intervals
        pivot_df = pivot_df.reindex(v_grid)

        # change df to contain the lats, longs, times and station numbers
        # Remove redundant operations and use loc directly
        metadata_df = transect_df.drop_duplicates(subset=['Institution_unique_identifier'])[
            ['LATITUDE', 'LONGITUDE', 'TIME', 'SOOP_line', 'SOOP_line_description',
             'Cruise_ID', 'Institution_unique_identifier', 'transect_id']
        ].reset_index(drop=True)

        # now use write2netcdf function to write the transect to a netcdf file
        write_vert_grid_nc(output_directory, metadata_df, pivot_df, globals_file_path='netcdfGlobalAtts.csv',
                        vars_file_path='netcdfVars.csv')


# create main function to call clean_and_bin_transect with input and output arguments
if __name__ == "__main__":

    if len(sys.argv) == 3:
        # input directory and output directory from command line arguments
        input_directory = sys.argv[1]
        output_folder = sys.argv[2]
        # Check if input_directory is a URL (THREDDS) or local path
        is_url = input_directory.startswith('http://') or input_directory.startswith('https://')
        if not is_url:
            clean_and_bin_transect(input_directory, output_folder)
        else:
            # go to the thredds server https://thredds.aodn.org.au/thredds/catalog/IMOS/SOOP/SOOP-XBT/DELAYED/catalog.html
            # go through each folder in the catalog and subfolders to create a list of input files with the full path
            # appended and then cycle through the full list of files to call clean_and_bin_transect
            base_url = input_directory

            response = requests.get(base_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a')
            input_directories = []
            for link in links:
                href = link.get('href')
                if href and href.endswith('catalog.html'):
                    # use base_url and remove 'catalog.html' to get the directory url
                    sub_url = base_url.rsplit('/', 1)[0] + '/' + href
                    sub_response = requests.get(sub_url)
                    sub_soup = BeautifulSoup(sub_response.text, 'html.parser')
                    sub_links = sub_soup.find_all('a')
                    for sub_link in sub_links:
                        sub_href = sub_link.get('href')
                        if sub_href and sub_href.endswith('catalog.html'):
                            # get the next level of the catalog
                            sub_sub_url = sub_url.rsplit('/', 1)[0] + '/' + sub_href
                            input_directories.append(sub_sub_url)
                        elif sub_href and sub_href.endswith('.nc'):
                            # if there are netcdf files directly in this folder, add this folder as input directory
                            input_directories.append(sub_url)
                            break  # no need to check further links in this folder
            # remove duplicates from input_directories
            input_directories = list(set(input_directories))
            # call clean_and_bin_transect for the full list of input directories
            clean_and_bin_transect(input_directories, output_folder)
    else:
        print("Usage: python clean_and_bin_transect.py <input_directory or input_url> <output_directory>")