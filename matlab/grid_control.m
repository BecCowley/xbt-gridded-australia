%% grid control script
transect = 'IX22-PX11';
if contains(transect,'PX34') | contains(transect,'PX32')
    indir = 'PX34_32';
else
    indir = transect;
end
  % create the paths
repo_root = fileparts(fileparts(mfilename('fullpath')));
data_env = getenv('XBT_DATA_DIR');
out_env = getenv('XBT_OUT_DIR');
if ~isempty(data_env)
    data_dir = fullfile(data_env, indir, 'transect_files');
else
    data_dir = fullfile(repo_root, 'data', indir, 'transect_files');
end
if ~isempty(out_env)
    out_data_dir = fullfile(out_env, indir, 'grid_simple');
else
    out_data_dir = fullfile(repo_root, 'output', indir, 'grid_simple');
end

%%
% remove any existing files in the output folder
if exist(out_data_dir, 'dir')
    delete(fullfile(out_data_dir, '*.mat'));
else
    warning(['Output folder does not exist, creating: ' out_data_dir]);
    mkdir(out_data_dir);
end
% check paths exist
if ~exist(data_dir,"dir")
    disp('data_dir for this transect does not exist')
    disp(data_dir)
    return
end
if ~exist(out_data_dir, 'dir')
    disp('out_data_dir for this transect does not exist')
    disp(out_data_dir)
    return
end 

% get the list of ascii filenames to process
fnames = dir(fullfile(data_dir, '*.nc'));
% Loop over the file names and extract the data
for a = 1:length(fnames)
    % skip over directories or files that are not nc files
    if ~contains(fnames(a).name, '.nc')
        continue
    end
    % get the full path name of the file
    infile = fullfile(fnames(a).folder, fnames(a).name);
    if exist(infile, 'file') == 2
        % read the data from the file
        xbt = nc2struct(infile, 1);

    else
        disp(['File: ' fnames(a).name ' does not exist'])
        continue
    end
    %out file
    outfile = fullfile(out_data_dir, xbt.atts.transect_id);

    % remove bad data currently at AODN. Will need updating when data is
    % replaced.
    trans_id = xbt.atts.transect_id;
    xbt = remove_bad_data(xbt, transect);
    if isempty(xbt)
        disp(['Entire transect removed from gridding ' trans_id])
        continue
    end
    % grid horizontally
    xbt = grid_simple(xbt,transect);
    % save if successfully gridded.
    if isfield(xbt,'TEMP_interp')
        save([outfile '.mat'],'xbt');
        disp([num2str(a) ' :Horizontal gridding completed: ' trans_id])
    else
        disp(['File ' trans_id ' not gridded'])
    end
end

% combine some transects split incorrectly
combine_transects(out_data_dir,transect);

%% join all the data together into one product
% clear
% transect = 'IX28';
if contains(transect,'PX32') | contains(transect,'PX34')
    indir = 'PX34_32';
else
    indir = transect;
end
% create the paths
if ~isempty(data_env)
    data_dir = fullfile(data_env, indir, 'transect_files');
else
    data_dir = fullfile(repo_root, 'data', indir, 'transect_files');
end
if ~isempty(out_env)
    out_data_dir = fullfile(out_env, indir, 'grid_simple');
else
    out_data_dir = fullfile(repo_root, 'output', indir, 'grid_simple');
end
filenames = dir(fullfile(out_data_dir, '*.mat'));

% Loop over the file names and extract the data
for a = 1:length(filenames)
    load(fullfile(filenames(a).folder, filenames(a).name))
    if a == 1
        temps = zeros(length(xbt.DEPTH),length(xbt.LAT_grid),length(filenames));
        [lons,lats] = deal(NaN*ones(length(xbt.LAT_grid),length(filenames)));
        lons_orig = [];lats_orig = [];
        depths = xbt.DEPTH;
        num_profiles = zeros(1,length(filenames));
    end
    temps(:,:,a) = xbt.TEMP_interp;
    lats(:,a) = xbt.LAT_grid;
    lons(:,a) = xbt.LON_grid;
    lats_orig = [lats_orig;xbt.LATITUDE];
    lons_orig = [lons_orig;xbt.LONGITUDE];
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
transect_id = transect_id(ind);
% remove data not in polygon
[temps,lats,lons,ti,num_profiles,transect_id] = check_transect_location(temps, lats,lons,ti,num_profiles,transect_id, transect);

% get bathymetry along reference transect
ref_locs = csvread(fullfile(repo_root, 'data', ['reference_lines_' transect '.csv']),1,0);
if contains(computer,'MACI64')
    bath = make_unique(-get_gebco_bathy(getenv('GEBCO_PATH'),ref_locs(:,1),ref_locs(:,2)));
else
    fnm = fullfile(repo_root, 'data','bath','gebco_2025_n21.2723_s-70.6943_w95.8777_e187.9369.nc');
    bath = make_unique(-get_gebco_bathy(fnm,ref_locs(:,1),ref_locs(:,2)));
end

% save to a mat file for plotting
save(fullfile(repo_root, 'output', indir, [transect '_all.mat']), ...
    "transect_id","ti", "lons", "lats","temps","depths","bath","ref_locs","num_profiles", ...
    "lons_orig","lats_orig")