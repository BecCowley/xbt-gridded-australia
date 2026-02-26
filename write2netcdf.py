# import a parquet file and write it to a netcdf file
import os
from time import strftime, gmtime
from pathlib import Path

import numpy as np
import pandas as pd
from netCDF4 import Dataset, date2num
from utils import read_variables_config, read_globals_config

def create_filename_output(df):

    # name format : IMOS_SOOP-XBT_T_20091223T140300Z_PX02_FV02_2025-02-01.nc
    # alternatively for CSIRO files:
    # PX02-202502-1.nc
    # where IMOS_SOOP-XBT_T is fixed
    # 20091223T140300Z is the time of first profile in the transect
    # PX02 is the SOOP line label
    # FV02 is the file version
    # 2025-02 is the transect ID

    # fv = 'FV02'
    #
    # filename = 'IMOS_SOOP-XBT_T_%s_%s_%s_ID-%s' % (
    #     min(df['TIME']).strftime('%Y%m%dT%H%M%SZ'), df['SOOP_line'][0], fv,
    #     df['transect_id'][0])
    # for CSIRO format, uncomment the following line and comment the previous one
    filename = '%s' % df['transect_id'][0]

    return filename


def write_vert_grid_nc(output_folder, transect_df, data_df, globals_file_path='netcdfGlobalAtts.csv', vars_file_path='netcdfVars.csv'):
    """output the binned data to the IMOS format netcdf version
    :param output_folder: the folder to write the netcdf file to
    :param transect_df: data frame with transect location and cruise information
    :param data_df: data frame with binned data for TEMP and DEPTH
    :param globals_file_path: path to the global attributes config file
    :param vars_file_path: path to the variable attributes config file
    :return: None
    """

    # now begin write out to new format
    netcdf_filepath = Path(output_folder) / f"{create_filename_output(transect_df)}.nc"
    print('Creating output %s' % str(netcdf_filepath))

    # read the variables config file
    vars = read_variables_config(vars_file_path)

    # read the global attributes config file
    globals_list = read_globals_config(globals_file_path)

    # Identify attribute columns starting with 'att_'
    att_cols = [col for col in vars.columns if col.startswith('att_')]
    # remove the 'att_' prefix from the attribute columns
    att_labels = [col.replace('att_', '') for col in att_cols]

    with Dataset(str(netcdf_filepath), "w", format="NETCDF4") as output_netcdf_obj:
        # Create the dimensions from the size of the data DataFrame
        depth_data = data_df.index.values

        # transform the TIME data to datetime objects in the dataframe
        transect_df['TIME'] = pd.to_datetime(transect_df['TIME'])
        # create DEPTH and TIME dimensions
        output_netcdf_obj.createDimension('DEPTH', len(depth_data))
        output_netcdf_obj.createDimension('TIME', None)

        # Create the variables from the vars Dataframe
        output_netcdf_obj.createVariable('TIME', 'f8', ('TIME',))
        output_netcdf_obj.createVariable('LATITUDE', 'f8', ('TIME',))
        output_netcdf_obj.createVariable('LONGITUDE', 'f8', ('TIME',))
        output_netcdf_obj.createVariable('TEMP', 'f4', ('TIME', 'DEPTH',), fill_value=np.float32(-9999.9))
        output_netcdf_obj.createVariable('DEPTH', 'f4', ('DEPTH',))

        # change NAN values in data_df to the missing value
        data_df = data_df.fillna(np.float32(-9999.9))

        # set variable attributes
        for var_name in vars['variable_name']:
            var_obj = output_netcdf_obj.variables[var_name]
            var_info = vars[vars['variable_name'] == var_name].iloc[0]
            # set attributes from the att_* columns
            for att_label, att_col in zip(att_labels, att_cols):
                att_value = var_info[att_col]
                if pd.isna(att_value):
                    continue
                var_obj.setncattr(att_label, att_value)

        # append the data to the file
        # first locate v in either transect_df or data_df
        for i, t in enumerate(transect_df['TIME']):
            output_netcdf_obj.variables['TIME'][i] = date2num(t, units=output_netcdf_obj.variables['TIME'].units,
                                                             calendar=output_netcdf_obj.variables['TIME'].calendar)
            output_netcdf_obj.variables['LATITUDE'][i] = transect_df['LATITUDE'].iloc[i]
            output_netcdf_obj.variables['LONGITUDE'][i] = transect_df['LONGITUDE'].iloc[i]
        output_netcdf_obj.variables['TEMP'][:,:] = data_df.values.T
        output_netcdf_obj.variables['DEPTH'][:] = depth_data


        # add geospatial information to global attributes dictionary
        globals_list['geospatial_lat_max'] = transect_df['LATITUDE'].max()
        globals_list['geospatial_lat_min'] = transect_df['LATITUDE'].min()
        globals_list['geospatial_lon_max'] = transect_df['LONGITUDE'].max()
        globals_list['geospatial_lon_min'] = transect_df['LONGITUDE'].min()
        globals_list['geospatial_vertical_max'] = max(depth_data)
        globals_list['geospatial_vertical_min'] = min(depth_data)
        # add time coverage information to global attributes dictionary
        globals_list['time_coverage_start'] = min(transect_df['TIME']).strftime("%Y-%m-%dT%H:%M:%SZ")
        globals_list['time_coverage_end'] = max(transect_df['TIME']).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Add date created to the global attributes
        utctime = strftime("%Y-%m-%dT%H:%M:%SZ", gmtime())
        globals_list['date_created'] = utctime

        # set the SOOP_line_label, SOOP_line_description and transect_id global attributes
        globals_list['SOOP_line_label'] = transect_df['SOOP_line'].iloc[0]
        globals_list['SOOP_line_description'] = transect_df['SOOP_line_description'].iloc[0]
        globals_list['transect_id'] = transect_df['transect_id'].iloc[0]
        globals_list['Cruise_ID'] = transect_df['Cruise_ID'].iloc[0]

        # set the global attributes where the index is the attribute name
        for att_name, att_value in globals_list.items():
            # if the global_att[att_name] is None, replace with 'Unknown'
            if pd.isna(att_value):
                att_value = 'Unknown'
            output_netcdf_obj.setncattr(att_name, att_value)
