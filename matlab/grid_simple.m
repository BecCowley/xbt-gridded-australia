function xbt = grid_simple(xbt,transect)
%
% read XBT transect data from netcdf FV02 files. Each file contains one
% transect of data on common depth grid.
%
% Inputs:
%   data_dir - path to folders containing *.nc grid files
%   out_data_dir - path to folder for output file
%
% Similar to GoShip Easy Ocean, complete a vertical and horizontal
% interpolation along the lat or lon grid.
% Bec Cowley, Jan 2026

% set up depending on transect
if contains('PX06',transect)
    orientation = 2; %North-south
    lat_grid = -32.5:0.1:-20;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
elseif contains('PX30',transect)
    orientation = 1; %east-west
    lon_grid = 153:0.1:178;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
elseif contains('PX34',transect)
    orientation = 1;
    lon_grid = 151.2:0.1:173;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
elseif contains('PX32',transect)
    orientation = 1;
    lon_grid = 151.2:0.1:172.4;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
elseif contains('PX32_34',transect)
    orientation = 1;
    lon_grid = 151.2:0.1:173;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
elseif contains('IX28', transect)
    orientation = 2; %North-south
    lat_grid = -66.5:0.1:-43.5;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
elseif contains('IX01',transect)
    orientation = 2; %North-south
    lat_grid = -35:0.5:-5;
    gaps = 6;
    e1 = 20; % 40 stations for frequently repeated
elseif contains('IX22-PX11',transect)
    orientation = 2; %North-south
    lat_grid = -20.9:0.5:29.26;
    gaps = 4;
    e1 = 20; % 40 stations for frequently repeated
elseif contains('PX02',transect)
    orientation = 1; %east-west
    lon_grid = 114.7:0.5:135.2;
    gaps = 4;
    e1 = 20; % 40 stations for frequently repeated
elseif contains('IX12',transect)
    orientation = 1; %East-west
    lon_grid = 50:0.5:116;
    gaps = 4;
    e1 = 20; % 40 stations for frequently repeated
else
    disp('transect argument is not coded in yet')
    return
end
% remove any profiles with less than 3 data points
irem = find(sum(~isnan(xbt.TEMP),1) < 2);
xbt.TEMP(:,irem) = [];
xbt.LONGITUDE(irem) = [];
xbt.LATITUDE(irem) = [];
xbt.TIME(irem) = [];

% ensure LONGITUDE is in 360 degrees
if any(xbt.LONGITUDE < 0)
    ineg = xbt.LONGITUDE < 0;
    xbt.LONGITUDE(ineg) = xbt.LONGITUDE(ineg) + 360;
end
% get terrainbase bathymetry at the deploy lon/lat
repo_root = fileparts(fileparts(mfilename('fullpath'))); % assumes matlab/ is inside repo root
gebco_env = getenv('GEBCO_PATH');
if ~isempty(gebco_env) && exist(gebco_env,'file')
    gebco_file = gebco_env;
else
    error(['GEBCO file not found. Set GEBCO_PATH environment variable or place file in "data/bath/" under the repo root: ' repo_root]);
end
bath = make_unique(-get_gebco_bathy(gebco_file,xbt.LATITUDE,xbt.LONGITUDE));
% sort data, remove shallow casts in deep water and make unique values
[xbt, bath] = sort_xbtdat(xbt,bath,orientation);    % create the complete lat/lon grid

% if the length of the profiles is <10
if length(xbt.TIME) < 5
    disp(['File: has less than 5 profiles'])
    return
end

lats = xbt.LATITUDE;
lons = xbt.LONGITUDE;

if orientation == 2 % interpolate by latitude
    % cut down the lat_grid to be within the chunk range
    % ig = lat_grid < max(lats) & lat_grid > min(lats);
    xbt.LAT_grid = lat_grid;
    xbt.LON_grid = interp1(lats, lons, lat_grid, 'linear');
    xbt.TEMP_interp = NaN*ones(length(xbt.DEPTH), length(lat_grid));
    xbt.bath = NaN*lat_grid;
    xtrans = lat_grid;
    ll = lats;
else % interpolate by longitude
    % cut down the lat_grid to be within the chunk range
    % ig = lon_grid < max(lons) & lon_grid > min(lons);
    xbt.LON_grid = lon_grid;
    xbt.LAT_grid = interp1(lons, lats, lon_grid, 'linear');
    xbt.TEMP_interp = NaN*ones(length(xbt.DEPTH),length(lon_grid));
    xbt.bath = NaN*lon_grid;
    xtrans = lon_grid;
    ll = lons;
end
% make a matrix of xbt.DEPTH to match the xbt.TEMP matrix with NaN in
% depth at same spots
deps = repmat(xbt.DEPTH,1,length(xbt.TIME));
deps(isnan(xbt.TEMP)) = NaN;

% Find where gaps exceed gaps
if orientation == 1
    diffs = [0, diff(lons')];  % prepend 0 for first station
else
    diffs = [0, diff(lats')];  % prepend 0 for first station
end
breakIdx = find(abs(diffs) >= gaps);
if ~isempty(breakIdx)
    % Convert boundary indices into chunk start/end pairs.
    % Example: if breakIdx = [5 12], then chunks are [1..4], [5..11], [12..N]
    N = numel(ll);
    chunkStarts = [1; breakIdx(:)];
    chunkEnds   = [breakIdx(:)-1; N];
    
    % Remove any empty/invalid chunks (can happen if break at 1)
    valid = chunkEnds >= chunkStarts;
    chunkStarts = chunkStarts(valid);
    chunkEnds   = chunkEnds(valid);
else
    chunkStarts = 1;
    chunkEnds   = length(diffs);
end

% interpolate in chunks, do not interpolate over regions > gaps
for ichunk = 1:numel(chunkStarts)
    istart = chunkStarts(ichunk);
    iend = chunkEnds(ichunk);
    idx = istart:iend;

    % skip if less than 2 locations in chunk
    if numel(idx) < 2
        continue
    end
    % get data in the chunk
    xmin = min(ll(idx));
    xmax = max(ll(idx));
    % grid chunk
    ingrid = (xtrans >= xmin) & (xtrans <= xmax);

        % interpolation
    % complete the spatial interpolation using objective mapping from Dean
    % Roemmich.
    dx = gsw_distance(lons(idx), lats(idx));
    x = [0, cumsum(dx')];

    la_grid = xbt.LAT_grid(ingrid);
    lo_grid = xbt.LON_grid(ingrid);

    if length(lo_grid) < 2
        return
    end
    dx = gsw_distance(lo_grid, la_grid);
    x1 = gsw_distance([lons(idx(1)), lo_grid(1)], [lats(idx(1)), la_grid(1)]);
    x_grid = [x1, cumsum(dx)];

    % interpolate onto new grid
    [xbt.TEMP_interp(:,ingrid),xbt.bath(ingrid)] = ...
        hinterp_objmap(xbt.TEMP(:,idx), make_unique(x), bath(idx), xbt.DEPTH, x_grid, e1);
end

end
%%
function [zinterp, maxpinterp] = hinterp_objmap(z, x, maxp, pr_grid, x_grid, efold1)
%
% Horizontal interpolation (no vertical interpolation) by objective mapping
%
% IN: z(:,:) measured (& vertically interpolated) at pr_grid(:) & x(:)
%   : maxpr(:) bottom pressure at x(:)
%
% OUT: zinterp(:,:) interpolated on pr_grid(:) and x_grid(:)
%      maxpinterp(:) bottom pressure at latlon(:)
%
%  Roemmich D., Optimal Estimation Of Hydrographic Station Data and Derived Fields,
%  Journal of Physical Oceanography, 13, 1544-1549, Aug 1983.
%
% Credit: GO-SHIP-Easy-Ocean https://github.com/kkats/GO-SHIP-Easy-Ocean

% constants
% efold1 = 40; % large e-folding scale
efold2 = 2; % small e-folding scale
evar1 = 0.1;
evar2 = 0.3; % 0.02 in Roemmich (1983)

% horizontal interpolation at constant pressure
zinterp = NaN(length(pr_grid), length(x_grid));

% station by station
for i = 1:(length(x)-1)
    % grids between i and (i+1)
    if i >= length(x) - 1
        ih = find(x(i) <= x_grid);
    else
        ih = find(x(i) <= x_grid & x_grid < x(i+1));
    end
    if isempty(ih)
        continue;
    end
    x_h = interp1([x(i), x(i+1)], [i, i+1], x_grid(ih)); % x_h now measured in station distance unit

    % six stations on both sides are included
    istart = max([1, (i-6)]);
    iend = min([i+7, length(x)]);
    irange = [istart:iend];
    xg = irange; % x is measured in station distance unit
    for j = 1:length(pr_grid)
        zg = z(j,irange);
        x1 = xg(:); z1 = zg(:); % column vector
        if all(isnan(z1))
            continue; % no extrapolation
        end
        ig = find(~isnan(z1));
        x1 = x1(ig); z1 = z1(ig);
        n = length(ig);
        xn = x1 * ones(1,n) - ones(n,1) * x1';
        % large scale
        gaus1 = exp(-xn.^2 / efold1^2);
        acov1 = gaus1 + diag(ones(n,1)) * evar1;
        mred = sum(acov1 \ z1) / sum(acov1 \ ones(n,1)); % spatial mean with red spectra (Bretherton et al., 1976)
        z1 = z1 - mred;
        w1 = acov1 \ z1;
        zlarge = gaus1 * w1;
        % small scale
        gaus2 = exp(-abs(xn) / efold2); % use exponential (Roemmich, 1983)
        acov2 = gaus2 + diag(ones(n,1)) * evar2;
        w2 = acov2 \ (z1 - zlarge);
        % gridding
        xh = ones(length(x_h),1) * x1' - x_h' * ones(1,n);
        zinterp(j,ih) = ones(size(ih')) * mred + exp(-xh.^2 / efold1^2) * w1 + exp(-abs(xh) / efold2) * w2;
    end 
end

% bottom depth
maxpinterp = interp1(x, maxp, x_grid, 'linear');

% mask all (spurious) data below bottom
for i = 1:length(x_grid)
    zinterp(find(pr_grid > maxpinterp(i)), i) = NaN;
end
end