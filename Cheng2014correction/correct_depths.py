# Perform depth and temperature correction using the Cheng 2014 procedure.

from pathlib import Path

import numpy as np
import pandas as pd


def _load_ch14_tables():
    base_dir = Path(__file__).resolve().parent
    fre_path = base_dir / 'FRE.csv'
    table1_path = base_dir / 'CH14_table1_update2023.txt'
    table2_path = base_dir / 'CH14_table2_update2023.txt'

    fre = pd.read_csv(fre_path, header=None, names=['ProbeType', 'H95A', 'H95B'])
    fre['ProbeType'] = fre['ProbeType'].astype(str).str.zfill(3)

    table1 = pd.read_csv(table1_path, sep=r'\s+', header=0)
    table2 = pd.read_csv(table2_path, sep=r'\s+', header=0)
    return fre, table1, table2


def depth_correction(depths, temperatures, timestamp, probe_type='052'):
    """Apply the Cheng 2014 depth and temperature corrections to one profile."""
    depths = np.asarray(depths, dtype=float)
    temperatures = np.asarray(temperatures, dtype=float)

    if depths.shape != temperatures.shape:
        raise ValueError('depths and temperatures must have the same shape')

    if not isinstance(probe_type, str):
        probe_type = str(probe_type).zfill(3)
    else:
        probe_type = probe_type.zfill(3)

    fre, table1, table2 = _load_ch14_tables()
    probe_type_num = int(float(probe_type))

    row = fre[fre['ProbeType'] == probe_type]
    if row.empty:
        raise ValueError(f'Unsupported probe type: {probe_type}')

    h95a = float(row['H95A'].iloc[0])
    h95b = float(row['H95B'].iloc[0]) * 0.001

    ts = pd.to_datetime(timestamp)
    year = int(ts.year)

    years = table1.iloc[:, 0].to_numpy(dtype=float)
    iyr = int(np.argmin(np.abs(years - year)))
    ch14_year = int(table1.iloc[iyr, 0])

    if probe_type_num in {42, 52}:
        coeff = 0.0025
        ch14_a_time = float(table1.iloc[iyr, 1])
        Bcoeff1 = 0.0070
        Bcoeff2 = 0.0440
        Ocoeff1 = 6.3765
        Ocoeff2 = 40.293
        Tbias_t_coeff1 = 0.0014
        Tbias_t_coeff2 = 0.0139
        tbias_time = float(table2.iloc[iyr, 1])
    elif probe_type_num in {2, 32}:
        coeff = 0.0050
        ch14_a_time = float(table1.iloc[iyr, 3])
        Bcoeff1 = 0.0069
        Bcoeff2 = 0.0435
        Ocoeff1 = 5.7914
        Ocoeff2 = 37.285
        Tbias_t_coeff1 = 0.00167
        Tbias_t_coeff2 = 0.0115
        tbias_time = float(table2.iloc[iyr, 3])
    elif probe_type_num == 11:
        coeff = 0.0044
        ch14_a_time = float(table1.iloc[iyr, 6])
        Bcoeff1 = 0.0046
        Bcoeff2 = 0.0293
        Ocoeff1 = 10.093
        Ocoeff2 = 66.4506
        Tbias_t_coeff1 = 0.0026
        Tbias_t_coeff2 = 0.0227
        tbias_time = float(table2.iloc[iyr, 6])
    elif probe_type_num == 61:
        coeff = 0.0050
        ch14_a_time = float(table1.iloc[iyr, 5])
        Bcoeff1 = 0.0069
        Bcoeff2 = 0.0435
        Ocoeff1 = 5.7914
        Ocoeff2 = 37.285
        Tbias_t_coeff1 = 0.00167
        Tbias_t_coeff2 = 0.0115
        tbias_time = float(table2.iloc[iyr, 5])
    elif probe_type_num == 71:
        coeff = 0.0050
        ch14_a_time = float(table1.iloc[iyr, 4])
        Bcoeff1 = 0.0069
        Bcoeff2 = 0.0435
        Ocoeff1 = 5.7914
        Ocoeff2 = 37.285
        Tbias_t_coeff1 = 0.00167
        Tbias_t_coeff2 = 0.0115
        tbias_time = float(table2.iloc[iyr, 4])
    elif probe_type_num == 222:
        coeff = 0.0025
        ch14_a_time = float(table1.iloc[iyr, 9])
        Bcoeff1 = 0.0034
        Bcoeff2 = 0.0204
        Ocoeff1 = 8.3176
        Ocoeff2 = 55.746
        Tbias_t_coeff1 = 0.0014
        Tbias_t_coeff2 = 0.0139
        tbias_time = float(table2.iloc[iyr, 9])
    else:
        raise ValueError(f'Unsupported probe type: {probe_type_num}')

    i100 = depths < 100
    t100 = np.nanmean(temperatures[i100]) if np.any(i100) else np.nan
    ch14_a_temp = t100 * coeff

    t = (h95a - np.sqrt(h95a**2 - (4 * -h95b) * depths)) / (2 * -h95b)
    A = h95a + ch14_a_time + ch14_a_temp
    B = A * Bcoeff1 - Bcoeff2
    Offset = A * Ocoeff1 - Ocoeff2

    depth_cor = A * t - B * t**2 - Offset

    Tbias_temp = temperatures * Tbias_t_coeff1 + Tbias_t_coeff2
    Tbias = tbias_time + Tbias_temp
    temp_cor = temperatures - Tbias

    return depth_cor, temp_cor, {
        'year': ch14_year,
        'A': A,
        'B': B,
        'Offset': Offset,
        't100': t100,
    }
