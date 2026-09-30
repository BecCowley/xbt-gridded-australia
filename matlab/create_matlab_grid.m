function create_matlab_grid(data_dir,out_data_dir, bathy_fnm, transects, remake)
% gridding of vertically interpolated XBT data onto spatial grid
%
% Inputs: 
%   data_dir: full path to directory containing the vertically gridded
%               netcdf files
%   out_data_dir: full path to directory to output *.mat files after
%               spatial gridding
%   bathy_fnm: path to bathymetry file including filename
%   transects: cell array of transect names to process 
%               (eg: {'IX01','PX02'}) or {} if all transects in the
%               data_dir to be processed
%   remake: logical. 1 = delete existing mat files in output dir and
%           re-grid. 2 = use existing mat files in output dir, do not 
%           re-grid but load from previously saved file and check data 
%           is within polygon and combine all occupations into a single 
%           .mat file.
%   
% Bec Cowley, June, 2026

arguments
    data_dir (1,1) string
    out_data_dir (1,1) string
    bathy_fnm (1,1) string
    transects cell = {}          % if empty, discover from data_dir
    remake (1,1) logical = true
end
% get the repo location
repo_root = fileparts(fileparts(mfilename('fullpath')));
% If transects not supplied, discover subdirectories in data_dir
if isempty(transects)
    d = dir(data_dir);
    transects = {d([d.isdir]).name};
    transects = transects(~ismember(transects, {'.','..'}));
end

for itrans = 1:length(transects)
    transect = transects{itrans};
    out_dir = fullfile(out_data_dir, transect);
    in_dir = fullfile(data_dir, transect);
    if remake
        % remove any existing files in the output folder
        delete(fullfile(out_dir, '*.mat'));
    end
    % check paths exist
    if ~exist(in_dir,"dir")
        disp('in_dir for this transect does not exist')
        disp(in_dir)
        return
    end
    if ~exist(out_dir, 'dir')
        mkdir(out_dir)
    end 
    % get key information for the transect
    settings = get_transect_settings(transect);
    if isempty(settings)
        continue
    end
    % get the bathymetry slice for this transect
    bathy = get_gebco_bathy_slice(bathy_fnm,settings.yp,settings.xp);

    % get the list of netcdf filenames to process
    if remake
        fnames = dir(fullfile(in_dir, '*.nc'));
    else
        fnames = dir(fullfile(in_dir, '*.mat'));
        fnames = fnames(~endsWith({fnames.name}, '_all.mat'));
    end
    if isempty(fnames)
        disp(['No files found in ' in_dir])
        return
    end
    first = true;
    clear ti lats_orig lons_orig transect_id
    % Loop over the file names and extract the data
    for a = 1:length(fnames)
        if remake
            % get the full path name of the file
            infile = [fnames(a).folder '/' fnames(a).name];
            if exist(infile, 'file') == 2
                % read the data from the file
                xbt = nc2struct(infile, 1);
        
            else
                disp(['File: ' fnames(a).name ' does not exist'])
                continue
            end

            %out file
            outfile = char(fullfile(out_dir, xbt.atts.transect_id));
            trans_id = xbt.atts.transect_id;

            if isempty(xbt)
                disp(['Entire occupation removed from gridding ' trans_id])
                continue
            end
            
            % grid horizontally
            xbt = grid_simple(xbt,bathy,settings);
            if isempty(xbt)
                continue
            end
            % save if successfully gridded.
            if isfield(xbt,'TEMP_interp')
                save([outfile '.mat'],'xbt');
                disp([num2str(a) ' :Horizontal gridding completed: ' trans_id])
            else
                disp(['File ' trans_id ' not gridded'])
            end
        else
            % give an update
            disp(['Loading ' fnames(a).name])
            % load the existing xbt file from saved version
            load(fullfile(out_dir, fnames(a).name), 'xbt')
        end

        if length(xbt.TIME) < 3
            disp(['Less than 3 profiles in ' fnames(a).name])
            continue
        end
        % join all the data together into one product
        if first
            temps = zeros(length(xbt.DEPTH),length(xbt.LAT_grid),length(fnames));
            [lons,lats,times] = deal(NaN*ones(length(xbt.LAT_grid),length(fnames)));
            lons_orig = [];lats_orig = [];times_orig = []; transect_id = [];
            depths = xbt.DEPTH;
            num_profiles = zeros(1,length(fnames));
            first = false;
        end
        if isfield(xbt,'TEMP_interp')
            temps(:,:,a) = xbt.TEMP_interp;
            lats(:,a) = xbt.LAT_grid;
            lons(:,a) = xbt.LON_grid;
            times(:,a) = datenum(xbt.TIME_grid);
        end
        lats_orig = [lats_orig;xbt.LATITUDE];
        lons_orig = [lons_orig;xbt.LONGITUDE];
        times_orig = [times_orig;xbt.TIME];
        % get the mean time for the transect
        ti(a) = mean(xbt.TIME);
        % transect id
        transect_id{a} = xbt.atts.transect_id;
        %number of profiles
        num_profiles(a) = length(xbt.TIME);
    end
    % sort the data by time
    [ti,ind] = sort(ti);
    temps = temps(:,:,ind);
    lats = lats(:,ind);
    lons = lons(:,ind);
    times = times(:,ind);
    transect_id = transect_id(ind);
    % remove data not in polygon
    [temps,lats,lons,times,num_profiles,ti,transect_id] = check_transect_location(temps, lats,lons,times,num_profiles,ti,transect_id, transect,settings);
    
    if isempty(temps)
        disp(['No data falls in the polygon for transect ' transect])
        continue
    end
    % get bathymetry along reference transect
    try
        ref_locs_fname = fullfile(repo_root, 'reference_lines', ['reference_lines_' transect '.csv']);
        ref_locs = csvread(ref_locs_fname,1,0);
    catch
        % build a reference line based on the data
        [ref_lats, ref_lons] = get_reference_line_from_latlon(lats, lons);
        ref_locs = [ref_lats, ref_lons];
    end
    bath = make_unique(-get_gebco_bathy(bathy,ref_locs(:,1),ref_locs(:,2)));
    
    % save to a mat file for plotting
    outfnm = fullfile(out_dir,[transect '_all.mat']);
    save(outfnm, ...
        "transect_id","ti","times", "lons", "lats","temps","depths","bath","ref_locs","num_profiles", ...
        "lons_orig","lats_orig","times_orig")
    disp(['Completed ' transect])
end
end
%%
function [latitudes, longitudes] = get_reference_line_from_latlon(lat_in, lon_in)
%GET_REFERENCE_LINE_FROM_LATLON Create a reference line from latitude/longitude arrays.
%
% Inputs:
%   lat_in   vector of latitudes
%   lon_in   vector of longitudes
%
% Outputs:
%   latitudes    reference line latitudes
%   longitudes   refe vbrence line longitudes

    % Ensure column vectors
    lat_in = lat_in(:);
    lon_in = lon_in(:);

    % Remove NaNs
    valid = ~isnan(lat_in) & ~isnan(lon_in);
    lat_in = lat_in(valid);
    lon_in = lon_in(valid);

    % Identify primary axis
    if max(lat_in) - min(lat_in) > max(lon_in) - min(lon_in)
        primary_axis = "LATITUDE";
        fprintf('Using LATITUDE as primary axis\n');
        primary_values = lat_in;
        secondary_values = lon_in;
    else
        primary_axis = "LONGITUDE";
        fprintf('Using LONGITUDE as primary axis\n');
        primary_values = lon_in;
        secondary_values = lat_in;
    end

    % Make primary axis monotonic and unique
    [primary_values, unique_idx] = unique(primary_values, 'stable');
    secondary_values = secondary_values(unique_idx);

    % Sort for interpolation
    [primary_values, sort_idx] = sort(primary_values);
    secondary_values = secondary_values(sort_idx);

    % Create reference points every 0.1 degrees
    primary_min = min(primary_values);
    primary_max = max(primary_values);
    primary_points = (primary_min:0.1:(primary_max + 0.1)).';

    % Interpolate secondary values
    secondary_points = interp1(primary_values, secondary_values, primary_points, 'linear', NaN);

    % Smooth with centered moving average, window = 3
    secondary_points = movmean(secondary_points, 3, 'omitnan');

    % Assign outputs
    if primary_axis == "LATITUDE"
        latitudes = primary_points;
        longitudes = secondary_points;
    else
        latitudes = secondary_points;
        longitudes = primary_points;
    end
end