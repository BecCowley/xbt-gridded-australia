# read in all netcdf files in the XBT transect, extract TEMP, DEPTH, LAT, LON, TIME, SOOP_line information.
# remove any bad data where TEMP_quality_control != 1, 2 or 5
# bin the data to 10 m vertical intervals using the bin_data_10m function from bin_data_10m.py
# output a single netcdf file with the cleaned and binned data, including the following variables:
# DEPTH (binned depth intervals), TEMP (binned temperatures), LAT, LON, TIME, SOOP_line
# include appropriate attributes for each variable and for the global file

import os
import sys
import re
import json
import traceback
import argparse
import numpy as np
import xarray as xr
import pandas as pd
from netCDF4 import num2date
from write2netcdf import write_vert_grid_nc
import requests
from bs4 import BeautifulSoup
from interp_gaussian import vinterp_gauss_simple
from urllib.parse import urljoin, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'matlab', 'Cheng2014correction'))
from Cheng2014correction.correct_depths import depth_correction


def parse_catalog_timestamp(timestamp_text):
    """Parse catalog/local timestamp text into a UTC pandas Timestamp."""
    if timestamp_text is None:
        return None

    if isinstance(timestamp_text, (int, float, np.integer, np.floating)):
        value = float(timestamp_text)
        abs_value = abs(value)
        # Heuristic for numeric epoch units: s, ms, us, ns.
        if abs_value >= 1e17:
            unit = 'ns'
        elif abs_value >= 1e14:
            unit = 'us'
        elif abs_value >= 1e11:
            unit = 'ms'
        else:
            unit = 's'
        ts = pd.to_datetime(value, unit=unit, errors='coerce', utc=True)
        if pd.isna(ts):
            return None
        return ts

    ts = pd.to_datetime(timestamp_text, errors='coerce', utc=True)
    if pd.isna(ts):
        return None
    return ts


def build_thredds_dodsc_url(catalog_url, href):
    """Convert a THREDDS catalog href into a full /thredds/dodsC URL."""
    if not href:
        return None

    parsed_catalog = urlparse(catalog_url)
    base = f"{parsed_catalog.scheme}://{parsed_catalog.netloc}"

    dataset_path = None
    if 'catalog.html?dataset=' in href:
        dataset_path = href.split('catalog.html?dataset=', 1)[-1]
    else:
        absolute_href = href if urlparse(href).scheme else urljoin(base, href)
        href_path = urlparse(absolute_href).path

        if '/thredds/catalog/' in href_path:
            dataset_path = href_path.split('/thredds/catalog/', 1)[-1]
        elif '/thredds/dodsC/' in href_path:
            dataset_path = href_path.split('/thredds/dodsC/', 1)[-1]
        elif href_path.endswith('.nc'):
            dataset_path = href_path.lstrip('/')

    if not dataset_path:
        return None

    dataset_path = dataset_path.replace('.html', '').lstrip('/')
    return f"{base}/thredds/dodsC/{dataset_path}"


def should_remove_stale_outputs(source_url):
    """Allow stale-output deletion except when the input URL is deeper than the base DELAYED catalogs or contains REALTIME data."""
    if not source_url or not source_url.startswith(('http://', 'https://')):
        return True

    parsed_source = urlparse(source_url)
    allowed_catalogs = [
        'https://thredds.aodn.org.au/thredds/catalog/IMOS/SOOP/SOOP-XBT/DELAYED/catalog.html'
    ]

    for allowed_url in allowed_catalogs:
        parsed_allowed = urlparse(allowed_url)
        allowed_parent = parsed_allowed.path.rsplit('/', 1)[0].rstrip('/') + '/'
        if parsed_source.scheme == parsed_allowed.scheme and parsed_source.netloc == parsed_allowed.netloc:
            if parsed_source.path == parsed_allowed.path:
                return True
            if parsed_source.path.startswith(allowed_parent):
                return False
            if 'REALTIME' in parsed_source.path:
                return False

    return True

def is_realtime(source_url):
    """Determine if the source URL indicates real-time data based on the presence of 'REALTIME' in the path."""
    if not source_url or not source_url.startswith(('http://', 'https://')):
        return False

    parsed_source = urlparse(source_url)
    if 'REALTIME' in parsed_source.path:
        return True

    return False

def discover_thredds_input_directories(base_url):
    """Recursively discover catalog URLs and netCDF file entries under a base THREDDS catalog."""
    base_parsed = urlparse(base_url)
    base_catalog_dir = base_parsed.path.rsplit('/', 1)[0].rstrip('/') + '/'

    def is_within_base_subtree(url):
        parsed = urlparse(url)
        if parsed.scheme != base_parsed.scheme or parsed.netloc != base_parsed.netloc:
            return False
        return parsed.path.startswith(base_catalog_dir)

    to_visit = [base_url]
    visited = set()
    input_directories = set()
    file_entries = []
    scanned_catalogs = 0

    while to_visit:
        catalog_url = to_visit.pop(0)
        if catalog_url in visited:
            continue
        visited.add(catalog_url)
        scanned_catalogs += 1

        if scanned_catalogs == 1 or scanned_catalogs % 25 == 0:
            print(
                f"Discovery progress: scanned {scanned_catalogs} catalogs, "
                f"queued {len(to_visit)}, found {len(file_entries)} files"
            )

        try:
            response = requests.get(catalog_url, timeout=60)
        except requests.RequestException as exc:
            print(f"Failed to access {catalog_url}: {exc}")
            continue

        if response.status_code != 200:
            print(f"Failed to access {catalog_url}: HTTP {response.status_code}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        has_netcdf = False
        current_catalog_path = urlparse(catalog_url).path
        current_catalog_dir = current_catalog_path.rsplit('/', 1)[0].rstrip('/') + '/'

        # Only inspect catalog listing rows (child entries), not global/navigation links.
        for row in soup.find_all('tr'):
            link = row.find('a')
            if not link:
                continue

            href = link.get('href')
            if not href:
                continue

            # Ignore parent-navigation and non-child absolute links.
            if href.startswith('../') or href.startswith('/'):
                continue

            link_url = urljoin(catalog_url, href)
            if not is_within_base_subtree(link_url):
                continue

            if '.nc' in href and 'TEST' not in href:
                file_url = build_thredds_dodsc_url(catalog_url, href)
                if not file_url:
                    continue
                
                # # if this is  a file from REALTIME, check the date of the file and do not include it if it is more than 10 days old, to avoid processing stale files that are still in the REALTIME catalog
                # if is_realtime(catalog_url):
                #     filename = os.path.basename(file_url)
                #     # get the timestamp from the filename, which is in the format IMOS_SOOP-XBT_T_20260309T222900Z_PX32_FV00_ID_9357951.nc
                #     match = re.search(r'_(\d{8}T\d{6}Z)_', filename)
                #     if match:
                #         file_timestamp_str = match.group(1)
                #         try:
                #             file_timestamp = datetime.strptime(file_timestamp_str, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
                #             if datetime.now(timezone.utc) - file_timestamp > pd.Timedelta(days=10):
                #                 print(f"Skipping stale REALTIME file: {file_url}")
                #                 continue
                #         except ValueError:
                #             print(f"Failed to parse timestamp from filename {filename}, including file by default.")

                updated_text = None
                cells = row.find_all('td')
                if len(cells) >= 3:
                    updated_text = cells[2].get_text(strip=True) or None

                file_entries.append({
                    'url': file_url,
                    'catalog_updated': updated_text
                })
                has_netcdf = True
                continue

            if href.endswith('catalog.html'):
                next_catalog_path = urlparse(link_url).path
                if next_catalog_path.startswith(current_catalog_dir) and link_url not in visited:
                    to_visit.append(link_url)

        if has_netcdf:
            input_directories.add(catalog_url)

    deduped_file_entries = {}
    for entry in file_entries:
        deduped_file_entries[entry['url']] = entry
    deduped_list = list(deduped_file_entries.values())

    print(
        f"Discovery complete: scanned {scanned_catalogs} catalogs, "
        f"found {len(input_directories)} directories with netCDF and {len(deduped_list)} files"
    )

    return sorted(input_directories), deduped_list


def discover_output_files(output_directory):
    """Find output .nc files recursively and index by transect_id in filename."""
    output_files = {}
    mode_pattern = re.compile(r'^(?P<transect_id>.+?)(?:_(?P<mode>D|R))?$')
    line_pattern = re.compile(r'^(?P<line>.+)-(?P<yearseq>[0-9]{6})$')

    for root, _, files in os.walk(output_directory):
        for filename in files:
            if not filename.endswith('.nc'):
                continue

            stem = filename[:-3]
            match = mode_pattern.match(stem)
            if match is None:
                continue

            transect_id = match.group('transect_id')
            mode = match.group('mode')
            line_match = line_pattern.match(transect_id)
            soop_line = line_match.group('line') if line_match else None

            path = os.path.join(root, filename)
            modified_time = pd.Timestamp.fromtimestamp(os.path.getmtime(path), tz='UTC')
            existing = output_files.get(transect_id)
            if existing is None:
                existing = {
                    'filename': filename,
                    'soop_line': soop_line,
                    'path': path,
                    'modified_time': modified_time,
                    'modes': set(),
                    'mode_paths': {},
                    'mode_modified_time': {}
                }
                output_files[transect_id] = existing
            else:
                if existing['modified_time'] < modified_time:
                    existing['filename'] = filename
                    existing['path'] = path
                    existing['modified_time'] = modified_time

            if mode is not None:
                previous_mode_time = existing['mode_modified_time'].get(mode)
                if previous_mode_time is None or modified_time > previous_mode_time:
                    existing['mode_paths'][mode] = path
                    existing['mode_modified_time'][mode] = modified_time
                existing['modes'].add(mode)

    return output_files


def extract_soop_line_from_transect_id(transect_id):
    """Extract SOOP line label from transect_id format line-YYYYNN."""
    if transect_id is None:
        return None
    transect_id = str(transect_id).strip()
    match = re.match(r'^(?P<line>.+)-[0-9]{6}$', transect_id)
    if not match:
        return None
    return match.group('line')


def load_local_index_file_entries(input_directories):
    """Load local file entries from xbt_file_index.json under input directories."""
    if not input_directories:
        raise ValueError("No input directories provided.")

    index_paths = [
        os.path.join(input_directory, 'xbt_file_index.json')
        for input_directory in input_directories
    ]
    existing_index_paths = [path for path in index_paths if os.path.exists(path)]
    if not existing_index_paths:
        raise FileNotFoundError(
            "Could not find xbt_file_index.json in input directories: "
            + ", ".join(input_directories)
        )

    file_entries = []
    for index_path in existing_index_paths:
        with open(index_path, 'r', encoding='utf-8') as handle:
            parsed = json.load(handle)

        if isinstance(parsed, dict):
            raw_entries = parsed.get('file_entries') or parsed.get('entries') or []
        elif isinstance(parsed, list):
            raw_entries = parsed
        else:
            raise ValueError(f"Unsupported JSON structure in {index_path}")

        base_dir = os.path.dirname(index_path)
        for raw in raw_entries:
            if not isinstance(raw, dict):
                continue
            
            # if the 'quality' value is 'bad', skip this entry as it contains no good data
            quality = raw.get('quality')
            if quality is not None and str(quality).strip().lower() == 'bad':
                continue
            
            path_like = raw.get('url') or raw.get('path') or raw.get('file_path') or raw.get('file_pth')
            if path_like is None:
                filename = raw.get('filename')
                if filename:
                    path_like = filename
            if not path_like:
                continue

            if path_like.startswith(('http://', 'https://')):
                file_url = path_like
            elif os.path.isabs(path_like):
                file_url = path_like
            else:
                file_url = os.path.join(base_dir, path_like)

            transect_id = raw.get('transect_id')
            if transect_id is not None:
                transect_id = str(transect_id).strip() or None

            file_entries.append({
                'url': file_url,
                'catalog_updated': (
                    raw.get('catalog_updated')
                    or raw.get('file_modified_time')
                    or raw.get('modified_time')
                    or raw.get('updated')
                ),
                'transect_id': transect_id,
                'soop_line': raw.get('SOOP_line_label') or raw.get('soop_line') or extract_soop_line_from_transect_id(transect_id),
            })

    # Keep the newest record per filename when duplicates exist across index files.
    deduped = {}
    for entry in file_entries:
        filename = os.path.basename(entry['url'])
        existing = deduped.get(filename)
        if existing is None:
            deduped[filename] = entry
            continue

        existing_ts = parse_catalog_timestamp(existing.get('catalog_updated'))
        new_ts = parse_catalog_timestamp(entry.get('catalog_updated'))
        if pd.isna(existing_ts) or (pd.notna(new_ts) and new_ts >= existing_ts):
            deduped[filename] = entry

    return list(deduped.values())


def read_output_file_info(output_filepath):
    """Read transect_id and filenames from an existing output netCDF file."""
    with xr.open_dataset(output_filepath, decode_cf=False) as ds:
        existing_transect_id = ds.attrs.get('transect_id')

        filename_values = ds['filename'].values
        time_mod = None
        if "file_updated" in ds.variables:
            raw_updated = np.asarray(ds['file_updated'].values).reshape(-1)
            updated_var = ds['file_updated']
            time_units = updated_var.attrs.get('units')
            time_cal = updated_var.attrs.get('calendar', 'UTC')
            if time_units is not None:
                try:
                    decoded_updated = num2date(
                        raw_updated.astype(float),
                        units=time_units,
                        calendar=time_cal,
                        only_use_cftime_datetimes=False
                    )
                    time_mod = pd.to_datetime(decoded_updated, errors='coerce', utc=True)
                except Exception:
                    time_mod = pd.to_datetime(raw_updated, errors='coerce', utc=True)
            else:
                time_mod = pd.to_datetime(raw_updated, errors='coerce', utc=True)

        existing_filename_map = {}
        rows = []
        for idx, row in enumerate(filename_values):
            if isinstance(row, (bytes, np.bytes_)):
                decoded = row.decode('utf-8', errors='ignore')
            elif hasattr(row, 'tobytes'):
                decoded = row.tobytes().decode('utf-8', errors='ignore')
            else:
                decoded = ''.join(chr(c) for c in row if c)

            cleaned = decoded.replace('\x00', '').strip()
            if cleaned:
                mt = pd.NaT
                if time_mod is not None and idx < len(time_mod):
                    mt = time_mod[idx]
                previous = existing_filename_map.get(cleaned)
                if previous is None or (pd.notna(mt) and (pd.isna(previous) or mt > previous)):
                    existing_filename_map[cleaned] = mt

        for filename, mt in sorted(existing_filename_map.items()):
            rows.append({'filename': filename, 'modified_time': mt})

    filename_df = pd.DataFrame(rows)
    if filename_df.empty:
        filename_df = pd.DataFrame({
            'filename': pd.Series(dtype='string'),
            'modified_time': pd.Series(dtype='datetime64[ns, UTC]')
        })
    else:
        filename_df['modified_time'] = pd.to_datetime(filename_df['modified_time'], errors='coerce', utc=True)

    return existing_transect_id, filename_df, existing_filename_map


def get_source_file_transect_id(filepath):
    """Read source transect_id attribute from an input netCDF file."""
    try:
        with xr.open_dataset(filepath, decode_cf=False) as ds:
            source_transect_id = ds.attrs.get('transect_id')
            if source_transect_id is None:
                return None
            source_transect_id = str(source_transect_id).strip()
            return source_transect_id or None
    except Exception as exc:
        print(f"Failed to read transect_id from {filepath}: {exc}")
        return None


def extract_probe_type_code(ds):
    """Parse the XBT probe type from the PROBE variable attribute 'PROBE_TYPE'."""
    if 'PROBE' not in ds.variables:
        return None
    attrs = ds['PROBE'].attrs
    probe_type = attrs.get('PROBE_TYPE')
    if probe_type is None:
        return None

    probe_type_str = str(probe_type).strip()
    if not probe_type_str:
        return None

    # Extract the first three digits from the probe type string
    match = re.search(r'(\d{3})', probe_type_str)
    if match:
        return match.group(1)

    return None


def extract_probe_manufacture_year(ds):
    """Extract the manufacture year from PROBE_manufacture_date_YYYYMMDD on the PROBE variable, if present."""
    if 'PROBE' not in ds.variables:
        return None
    value = ds['PROBE'].attrs.get('PROBE_manufacture_date_YYYYMMDD')
    if value is None:
        return None
    value = str(value).strip()
    return value[:4] if value else None


def extract_soop_line_from_filename(filename):
    """Extract SOOP line token located between the 4th and 5th underscores."""
    parts = filename.split('_')
    if len(parts) == 6:
        return parts[3]
    elif len(parts) >= 7:
        return parts[4]
    return None


# Extract file processing into separate function for parallelization
def process_single_file(filepath, v_grid, catalog_updated=None, source_transect_id=None):
    """Process a single netCDF file and return extracted data"""
    try:
        with xr.open_dataset(filepath) as ds:
            # Extract variables
            depths = ds['DEPTH'].values
            temperatures = ds['TEMP'].values.flatten()
            temp_quality_control = ds['TEMP_quality_control'].values.flatten()
            lat = np.asarray(ds['LATITUDE'].values).squeeze().item()
            lon = np.asarray(ds['LONGITUDE'].values).squeeze().item()
            time = np.asarray(ds['TIME'].values).squeeze().item()
            probe_type_code = extract_probe_type_code(ds)
            manufacture_year = extract_probe_manufacture_year(ds)
            correction_timestamp = manufacture_year if manufacture_year is not None else time
            if source_transect_id is None:
                source_transect_id = ds.attrs.get('transect_id')
                if source_transect_id is not None:
                    source_transect_id = str(source_transect_id).strip() or None

            if 'XBT_uniqueid' in ds.attrs:
                station_number = ds.attrs.get('XBT_uniqueid', 'Unknown')
            else:
                station_number = ds.attrs.get('Institution_unique_identifier', '')

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
            elif 'Ship' in ds.variables and 'Cruise_ID' in ds['Ship'].attrs:
                cruise_id = ds['Ship'].attrs.get('Cruise_ID', 'Unknown')
            else:
                # probably real time data, use the callsign as a proxy for cruise_id if available
                cruise_id = ds.attrs.get('Callsign', 'Unknown')

        # apply the Cheng 2014 depth and temperature correction ahead of vertical interpolation
        corrected_depths, corrected_temperatures = depths, temperatures
        if probe_type_code is not None:
            try:
                corrected_depths, corrected_temperatures, _ = depth_correction(depths, temperatures, correction_timestamp, probe_type_code)
            except ValueError as exc:
                print(f'Skipping CH14 correction for {filepath}: {exc}')
        else:
            print(f'No XBT probe type attribute found in {filepath}; skipping CH14 correction')
        
        # Remove bad data where TEMP_quality_control is not 0, 1, 2, or 5 and where temperatures are less than -5 or greater than 40
        valid_mask = np.isin(temp_quality_control, [0, 1, 2, 5]) & (temperatures >= -5) & (temperatures <= 40)
        depths = depths[valid_mask]
        temperatures = temperatures[valid_mask]
        corrected_depths = corrected_depths[valid_mask]
        corrected_temperatures = corrected_temperatures[valid_mask]

        # if there is no valid data, return None
        if len(temperatures) == 0:
            print('No valid temperature data in file: %s' % filepath)
            return None

        # grid the uncorrected data first so it is unaffected by the CH14 correction below
        interp_temps_uncorrected = vinterp_gauss_simple(depths, temperatures, v_grid, half_width=11)

        # return interpolated gaussian smoothed data on with 10m intervals from 0 to 1800m
        interp_temps = vinterp_gauss_simple(corrected_depths, corrected_temperatures, v_grid, half_width=11)

        # Return structured data instead of appending to lists
        return {
            'temps': interp_temps,
            'temps_uncorrected': interp_temps_uncorrected,
            'lat': lat,
            'lon': lon,
            'time': time,
            'soop_line': soop_line,
            'soop_line_description': soop_line_description,
            'cruise_id': cruise_id,
            'station_number': station_number,
            'transect_id': source_transect_id,
            'catalog_updated': catalog_updated,
            'filename': os.path.basename(filepath)
        }
    except Exception as e:
        print(f'Error processing file {filepath}: {type(e).__name__}: {e}')
        print(traceback.format_exc())
        return None
    
    
def clean_and_grid_transect(input_directories, output_directory, file_entries=None, v_grid_step=10, max_depth=1800, source_url=None):
    # Check if input_directory is a URL (THREDDS) or local path
    is_url = bool(input_directories) and (
        input_directories[0].startswith('http://') or input_directories[0].startswith('https://')
    )

    # Build file entries first so reprocessing checks can run at the start.
    if is_url:
        if file_entries is None:
            print("No pre-discovered file entries provided; discovering from catalogs now...")
            file_entries = []
            for input_directory in input_directories:
                _, discovered_entries = discover_thredds_input_directories(input_directory)
                file_entries.extend(discovered_entries)
    else:
        file_entries = load_local_index_file_entries(input_directories)

    # Build source file table for update checks.
    file_entries_df = pd.DataFrame([
        {
            'url': entry['url'],
            'filename': os.path.basename(entry['url']),
            'modified_time': parse_catalog_timestamp(entry.get('modified_time') or entry.get('catalog_updated')),
            'SOOP_line': entry.get('soop_line') or extract_soop_line_from_transect_id(entry.get('transect_id')) or extract_soop_line_from_filename(os.path.basename(entry['url'])),
            'source_transect_id': entry.get('transect_id')
        }
        for entry in file_entries
    ])
    if file_entries_df.empty:
        print("No source files found to process.")
        return

    # Keep newest source timestamp per filename.
    file_entries_df = file_entries_df.sort_values(by='modified_time').drop_duplicates(subset=['filename'], keep='last')

    # Discover existing outputs recursively by transect filename pattern
    existing_output_files = discover_output_files(output_directory)

    # Read output filename variables and identify files missing filename metadata
    output_file_cache = {}
    for transect_id, output_info in existing_output_files.items():
        existing_transect_id, output_filename_df, output_filename_modified_map = read_output_file_info(output_info['path'])
        output_filenames = set(output_filename_modified_map.keys())
        cache_transect_id = existing_transect_id if existing_transect_id else transect_id
        output_file_cache[cache_transect_id] = {
            'existing_transect_id': existing_transect_id,
            'filename_df': output_filename_df,
            'filenames': output_filenames,
            'filename_modified_map': output_filename_modified_map,
            'path': output_info['path'],
            'modified_time': output_info['modified_time'],
            'modes': output_info.get('modes', set()),
            'mode_paths': output_info.get('mode_paths', {})
        }

    # Build a cached filename table once to avoid repeated nested loops.
    cached_rows = []
    for transect_id, output_info in output_file_cache.items():
        for filename in output_info['filenames']:
            cached_rows.append({
                'filename': filename,
                'transect_id': transect_id,
                'cached_modified_time': output_info['filename_modified_map'].get(filename)
            })

    cached_filename_df = pd.DataFrame(cached_rows)
    if cached_filename_df.empty:
        cached_filename_df = pd.DataFrame({
            'filename': pd.Series(dtype='string'),
            'transect_id': pd.Series(dtype='string'),
            'cached_modified_time': pd.Series(dtype='datetime64[ns, UTC]')
        })
    else:
        cached_filename_df['cached_modified_time'] = pd.to_datetime(
            cached_filename_df['cached_modified_time'], errors='coerce', utc=True
        )

    source_filename_df = file_entries_df[['url', 'filename', 'modified_time', 'source_transect_id']].copy()
    source_filenames = set(source_filename_df['filename'].tolist())
    cached_filenames = set(cached_filename_df['filename'].tolist())

    # Step 2: identify added/removed/updated filenames against cache.
    added_filenames = source_filenames - cached_filenames
    removed_filenames = cached_filenames - source_filenames

    common_df = source_filename_df[['filename', 'modified_time']].merge(
        cached_filename_df,
        on='filename',
        how='inner'
    )
    # Compare timestamps at minute resolution without rounding or flooring.
    common_modified_time = common_df['modified_time'].dt.strftime('%Y-%m-%d %H:%M')
    common_cached_modified_time = common_df['cached_modified_time'].dt.strftime('%Y-%m-%d %H:%M')
    updated_df = common_df[
        pd.notna(common_df['modified_time'])
        & (
            pd.isna(common_df['cached_modified_time'])
            | (common_modified_time > common_cached_modified_time)
        )
    ]
    updated_filenames = set(updated_df['filename'].tolist())

    # A file moving from one transect_id to another requires both old and new outputs to be remade.
    transect_compare_df = source_filename_df[['filename', 'source_transect_id']].merge(
        cached_filename_df[['filename', 'transect_id']],
        on='filename',
        how='inner'
    )
    moved_df = transect_compare_df[
        pd.notna(transect_compare_df['source_transect_id'])
        & pd.notna(transect_compare_df['transect_id'])
        & (transect_compare_df['source_transect_id'] != transect_compare_df['transect_id'])
    ]
    moved_filenames = set(moved_df['filename'].tolist())

    # Step 3: removed/updated files map to cached transects; include all filenames in those transects.
    removed_transects = set(
        cached_filename_df.loc[
            cached_filename_df['filename'].isin(removed_filenames),
            'transect_id'
        ].tolist()
    )
    updated_transects = set(updated_df['transect_id'].tolist())
    moved_old_transects = set(moved_df['transect_id'].tolist())
    impacted_cached_transects = removed_transects | updated_transects | moved_old_transects

    impacted_cached_filenames = set(
        cached_filename_df.loc[
            cached_filename_df['transect_id'].isin(impacted_cached_transects),
            'filename'
        ].tolist()
    )

    # Step 4: only for new files, read transect_id from source when not provided by index.
    explicit_urls_to_process = set()
    new_source_transect_id_cache = {}
    added_entries_df = source_filename_df[source_filename_df['filename'].isin(added_filenames)]
    for entry in added_entries_df.itertuples(index=False):
        explicit_urls_to_process.add(entry.url)
        source_transect_id = entry.source_transect_id
        if source_transect_id is None:
            source_transect_id = get_source_file_transect_id(entry.url)
        new_source_transect_id_cache[entry.url] = source_transect_id

    # If a new file belongs to an existing cached transect, also refresh that transect's source files.
    new_source_transects = {
        tid for tid in new_source_transect_id_cache.values() if tid is not None
    }
    new_existing_cached_transects = new_source_transects & set(output_file_cache.keys())
    if new_existing_cached_transects:
        impacted_cached_transects.update(new_existing_cached_transects)
        impacted_cached_filenames.update(
            cached_filename_df.loc[
                cached_filename_df['transect_id'].isin(new_existing_cached_transects),
                'filename'
            ].tolist()
        )

    cached_urls_to_process = set(
        source_filename_df.loc[
            source_filename_df['filename'].isin(impacted_cached_filenames),
            'url'
        ].tolist()
    )

    changed_source_transects = set(
        source_filename_df.loc[
            source_filename_df['filename'].isin(added_filenames | moved_filenames),
            'source_transect_id'
        ].dropna().tolist()
    )
    changed_source_transects.update(new_source_transect_id_cache.values())
    changed_source_transects.discard(None)

    source_transect_urls_to_process = set(
        source_filename_df.loc[
            source_filename_df['source_transect_id'].isin(changed_source_transects),
            'url'
        ].tolist()
    )

    urls_to_process = explicit_urls_to_process | cached_urls_to_process | source_transect_urls_to_process

    if impacted_cached_transects or explicit_urls_to_process:
        original_count = len(file_entries)
        file_entries = [
            entry for entry in file_entries
            if entry['url'] in urls_to_process
        ]
        print(
            f"Detected changes in {len(added_filenames)} added, {len(updated_filenames)} updated, "
            f"{len(removed_filenames)} removed source filenames; "
            f"{len(moved_filenames)} moved between transect_id values; "
            f"{len(impacted_cached_transects)} cached transects require reprocessing; "
            f"processing {len(file_entries)} of {original_count} source files"
        )

        # If an impacted transect has no remaining source files, remove stale output only when allowed.
        if should_remove_stale_outputs(source_url):
            active_source_filenames = set(source_filename_df['filename'].tolist())
            active_source_transects = set(
                cached_filename_df.loc[
                    cached_filename_df['transect_id'].isin(impacted_cached_transects)
                    & cached_filename_df['filename'].isin(active_source_filenames),
                    'transect_id'
                ].tolist()
            )
            stale_transects = impacted_cached_transects - active_source_transects
            for stale_transect in stale_transects:
                stale_info = output_file_cache.get(stale_transect)
                if stale_info and os.path.exists(stale_info['path']):
                    os.remove(stale_info['path'])
                    print(f"Removed stale output for transect {stale_transect}: {stale_info['path']}")
        else:
            print("Skipping stale output removal because the input URL is deeper than the base REALTIME/DELAYED catalogs.")
    else:
        print("No transects require reprocessing after cache/source comparison.")
        return

    # Rebuild source file table for the selected files only.
    file_entries_df = pd.DataFrame([
        {
            'url': entry['url'],
            'filename': os.path.basename(entry['url']),
            'updated_ts': parse_catalog_timestamp(entry.get('modified_time') or entry.get('catalog_updated')),
            'SOOP_line': entry.get('soop_line') or extract_soop_line_from_transect_id(entry.get('transect_id')) or extract_soop_line_from_filename(os.path.basename(entry['url'])),
            'source_transect_id': entry.get('transect_id')
        }
        for entry in file_entries
    ])


    # Pre-define v_grid outside of loop for reuse
    v_grid = np.arange(0, max_depth + v_grid_step, v_grid_step)

    # Loop over the SOOP lines
    for soop_line in file_entries_df['SOOP_line'].dropna().unique():
        print(f"SOOP line: {soop_line}")

        # subset the file entries for this SOOP line
        line_file_entries_df = file_entries_df[file_entries_df['SOOP_line'] == soop_line]
        # Serial file processing to avoid threading issues with remote/HDF5 reads
        print(f"Processing {len(line_file_entries_df)} files serially...")
        profile_results = []
        for entry in line_file_entries_df.itertuples(index=False):
            result = process_single_file(entry.url, v_grid, entry.updated_ts, source_transect_id=entry.source_transect_id)
            if result is not None:
                profile_results.append(result)
        # if no records, exit early
        if not profile_results:
            print("No valid data extracted for this SOOP line, skipping output.")
            continue

        # Keep one row per profile and defer depth expansion to transect write-out.
        profiles_df = pd.DataFrame({
            'TEMP_PROFILE': [np.asarray(r['temps'], dtype=np.float32) for r in profile_results],
            'TEMP_PROFILE_uncorrected': [np.asarray(r['temps_uncorrected'], dtype=np.float32) for r in profile_results],
            'LATITUDE': np.asarray([r['lat'] for r in profile_results], dtype=np.float32),
            'LONGITUDE': np.asarray([r['lon'] for r in profile_results], dtype=np.float32),
            'TIME': pd.to_datetime([r['time'] for r in profile_results]),
            'SOOP_line': [r['soop_line'] for r in profile_results],
            'SOOP_line_description': [r['soop_line_description'] for r in profile_results],
            'Cruise_ID': [r['cruise_id'] for r in profile_results],
            'Institution_unique_identifier': [r['station_number'] for r in profile_results],
            'transect_id': [r['transect_id'] for r in profile_results],
            'filename': [r['filename'] for r in profile_results],
            'catalog_updated': pd.to_datetime([r['catalog_updated'] for r in profile_results], errors='coerce', utc=True)
        })
        profiles_df['SOOP_line'] = profiles_df['SOOP_line'].astype('category')
        profiles_df['SOOP_line_description'] = profiles_df['SOOP_line_description'].astype('category')
        profiles_df['Cruise_ID'] = profiles_df['Cruise_ID'].astype('category')
        profiles_df = profiles_df.sort_values(by='TIME').reset_index(drop=True)

        missing_transect = profiles_df['transect_id'].isna()
        if missing_transect.any():
            missing_count = int(missing_transect.sum())
            print(f"Skipping {missing_count} profiles without transect_id for SOOP line {soop_line}.")
            profiles_df = profiles_df.loc[~missing_transect].copy()
        if profiles_df.empty:
            print("No profiles with transect_id available after filtering, skipping output.")
            continue

        unique_transects = profiles_df['transect_id'].dropna().unique()
        
        # check realtime data for transects with less than 5 profiles and remove these. 
        if is_realtime(source_url):
            transect_counts = profiles_df['transect_id'].value_counts()
            small_transects = transect_counts[transect_counts < 5].index.tolist()
            if small_transects:
                print(f"Removing {len(small_transects)} small transects with less than 5 profiles: {small_transects}")
                profiles_df = profiles_df[~profiles_df['transect_id'].isin(small_transects)]
                unique_transects = profiles_df['transect_id'].dropna().unique()

        # for each unique transect, write out the data to a netcdf file
        print(f"Writing {len(unique_transects)} transects to netCDF files...")
        source_is_realtime = is_realtime(source_url)
        source_is_delayed = not source_is_realtime
        for transect in unique_transects:
            existing_output = output_file_cache.get(transect, {})
            existing_modes = existing_output.get('modes', set())

            # If delayed-mode output exists, do not write a realtime replacement for this transect.
            if source_is_realtime and 'D' in existing_modes:
                print(f"Transect {transect} has delayed output; skipping realtime processing to avoid overwrite.")
                continue

            # If processing delayed data and a realtime output exists, remove it so delayed replaces it.
            if source_is_delayed and 'R' in existing_modes:
                realtime_output_path = existing_output.get('mode_paths', {}).get('R')
                if realtime_output_path and os.path.exists(realtime_output_path):
                    os.remove(realtime_output_path)
                    print(f"Removed realtime output for transect {transect} so delayed output can replace it: {realtime_output_path}")
            
            # if Realtime and the number of profiles in source is less than the number in the existing cache for this transect, skip writing 
            if source_is_realtime and 'R' in existing_modes:
                existing_profile_count = len(existing_output.get('filenames', []))
                current_profile_count = len(profiles_df.loc[profiles_df['transect_id'] == transect])
                if current_profile_count < existing_profile_count:
                    print(f"Skipping write for realtime transect {transect} because it has fewer profiles ({current_profile_count}) than existing cache ({existing_profile_count}).")
                    continue
            
            transect_profiles = profiles_df.loc[
                profiles_df['transect_id'] == transect
            ].sort_values(by='TIME').reset_index(drop=True)
            if transect_profiles.empty:
                continue

            transect_profiles['profile_number'] = np.arange(1, len(transect_profiles) + 1, dtype=np.int32)

            temp_matrix = np.vstack(transect_profiles['TEMP_PROFILE'].to_numpy())
            pivot_df = pd.DataFrame(
                temp_matrix.T,
                index=v_grid,
                columns=transect_profiles['TIME'].to_numpy()
            )

            temp_matrix_uncorrected = np.vstack(transect_profiles['TEMP_PROFILE_uncorrected'].to_numpy())
            pivot_df_uncorrected = pd.DataFrame(
                temp_matrix_uncorrected.T,
                index=v_grid,
                columns=transect_profiles['TIME'].to_numpy()
            )

            metadata_df = transect_profiles[
                ['LATITUDE', 'LONGITUDE', 'TIME', 'SOOP_line', 'SOOP_line_description',
                'Cruise_ID', 'Institution_unique_identifier', 'transect_id', 'filename', 'profile_number', 'catalog_updated']
            ].reset_index(drop=True)

            # now use write2netcdf function to write the transect to a netcdf file
            write_vert_grid_nc(output_directory, metadata_df, pivot_df, data_df_uncorrected=pivot_df_uncorrected,
                            globals_file_path='netcdfGlobalAtts.csv', vars_file_path='netcdfVars.csv', source_url=source_url)


# create main function to call clean_and_grid_transect with input and output arguments
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean, vertically grid, and write XBT transects to netCDF."
    )
    parser.add_argument(
        "input_directory",
        help="Input directory or THREDDS catalog URL"
    )
    parser.add_argument(
        "output_directory",
        help="Output directory for gridded transect netCDF files"
    )
    parser.add_argument(
        "--v-grid-step",
        dest="v_grid_step",
        type=int,
        default=10,
        help="Vertical grid spacing in meters (default: 10)"
    )
    parser.add_argument(
        "--max-depth",
        dest="max_depth",
        type=int,
        default=1800,
        help="Maximum depth in meters for the vertical grid (default: 1800)"
    )

    args = parser.parse_args()

    if args.v_grid_step <= 0:
        parser.error("--v-grid-step must be a positive integer")
    if args.max_depth <= 0:
        parser.error("--max-depth must be a positive integer")

    input_directory = args.input_directory
    output_folder = args.output_directory

    # Check if input_directory is a URL (THREDDS) or local path
    is_url = input_directory.startswith('http://') or input_directory.startswith('https://')
    if not is_url:
        # for the input directory, go through the subfolders and perform the clean_and_grid_transect function for each subfolder
        directory_list = []
        for root, dirs, files in os.walk(input_directory):
            if 'xbt_file_index.json' in files:
                directory_list.append(root)
                # don't keep walking into subdirectories once an index file is found
                dirs[:] = []
        if not directory_list:
            print(f"No subdirectories with xbt_file_index.json found in {input_directory}")
            sys.exit(1)
        clean_and_grid_transect(
            directory_list,
            output_folder,
            v_grid_step=args.v_grid_step,
            max_depth=args.max_depth,
            source_url=input_directory
        )
    else:
        # go to the thredds server https://thredds.aodn.org.au/thredds/catalog/IMOS/SOOP/SOOP-XBT/DELAYED/catalog.html
        # go through each folder in the catalog and subfolders to create a list of input files with the full path
        # appended and then cycle through the full list of files to call clean_and_grid_transect
        base_url = input_directory
        print(f"Discovering files from THREDDS catalog at {base_url}...")
        input_directories, file_entries = discover_thredds_input_directories(base_url)
        if not file_entries:
            print(f"No valid netCDF-containing catalogs found under {base_url}")
            sys.exit(1)
        # # limit input_directories to just the first 1 for testing
        # input_directories = input_directories[:1]
        # call clean_and_grid_transect for the full list of input directories
        clean_and_grid_transect(
            input_directories,
            output_folder,
            file_entries=file_entries,
            v_grid_step=args.v_grid_step,
            max_depth=args.max_depth,
            source_url=input_directory
        )
