function time_datetime = read_netcdf_time(filename, time_var_name)
    % READ_NETCDF_TIME Reads time data from a NetCDF file and converts it to datetime objects.

    % 1. Read the raw time values
    time_numeric = ncread(filename, time_var_name);

    % 2. Read the time attributes (units and calendar)
    try
        units_attr = ncreadatt(filename, time_var_name, 'units');
    catch
        error('Time variable must have a "units" attribute.');
    end

    try
        calendar_attr = ncreadatt(filename, time_var_name, 'calendar');
    catch
        % Assume default Gregorian calendar if not specified
        calendar_attr = 'gregorian';
    end

    % 3. Parse the units string to get the time unit and reference date (epoch)
    % Example units: 'days since 1900-01-01 00:00:00'
    unit_parts = strsplit(units_attr, ' since ');
    if numel(unit_parts) < 2
        error('Units attribute is not in the expected format (e.g., "days since YYYY-MM-DD").');
    end

    time_unit = unit_parts{1};
    reference_date = unit_parts{2};
    % split the reference_date_str to remove 'UTC'
    reference_date_str = strsplit(reference_date, ' UTC');
    reference_date_str = reference_date_str{1};

    % Convert the reference date string to a datetime object
    % datetime automatically handles various input formats
    try
        reference_date = datetime(reference_date_str, 'TimeZone', 'UTC'); % Assuming UTC
    catch
        error('Could not parse reference date from units attribute.');
    end

    % 4. Convert the numeric time values to datetime objects using the units
    switch lower(time_unit)
        case {'days', 'day'}
            time_datetime = reference_date + days(time_numeric);
        case {'hours', 'hour'}
            time_datetime = reference_date + hours(time_numeric);
        case {'minutes', 'minute'}
            time_datetime = reference_date + minutes(time_numeric);
        case {'seconds', 'second'}
            time_datetime = reference_date + seconds(time_numeric);
        case {'milliseconds', 'millisecond'}
            time_datetime = reference_date + milliseconds(time_numeric);
        case {'microseconds', 'microsecond'}
            time_datetime = reference_date + microseconds(time_numeric);
        otherwise
            % Note: "months" and "years" can be problematic due to variable length
            warning('Unsupported time unit "%s". Returning raw numeric data.', time_unit);
            time_datetime = time_numeric;
            return;
    end

    % 5. Handle the 'calendar' attribute
    % MATLAB's datetime uses the proleptic Gregorian calendar by default.
    % If the NetCDF file uses a different calendar (e.g., '365_day', 'noleap'),
    % manual adjustment or specific toolboxes (like the CDT toolbox mentioned in the search results) may be required.
    if ~isequal(lower(calendar_attr), 'gregorian')
       warning('Non-gregorian calendar "%s" detected. Manual adjustment may be needed.', calendar_attr);
    end
end
