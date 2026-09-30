function deps = get_gebco_bathy(bathy, lats, lons)
% get bathymetry values from a preloaded GEBCO bathymetry slice
% inputs:
%   bathy = struct containing:
%       bathy.z   = bathymetry values
%       bathy.lat = latitude vector for the slice
%       bathy.lon = longitude vector for the slice
%   lats  = latitudes of locations to retrieve
%   lons  = longitudes of locations to retrieve
% Bec Cowley, October, 2025

deps = nan(size(lons));

if isempty(lats) || isempty(lons)
    return
end

req = {'lat','lon','z'};
for k = 1:numel(req)
    if ~isfield(bathy, req{k})
        error('Bathymetry slice struct must contain fields: lat, lon, z');
    end
end

out_sz = size(lons);
latsq = double(lats(:));
lonsq = double(lons(:));

lat_sub = double(bathy.lat(:));
lon_sub = double(bathy.lon(:));
z = double(bathy.z);

% Match longitude convention of provided slice
lon_min = min(lon_sub);
lon_max = max(lon_sub);
lon_is_360 = lon_min >= 0 && lon_max > 180;

if lon_is_360
    lonsq(lonsq < 0) = lonsq(lonsq < 0) + 360;
else
    lonsq(lonsq > 180) = lonsq(lonsq > 180) - 360;
end

in = lonsq >= min(lon_sub) & lonsq <= max(lon_sub) & ...
     latsq >= min(lat_sub) & latsq <= max(lat_sub);

if ~any(in)
    deps = reshape(deps, out_sz);
    return
end

lon_sub(lon_sub == 0) = -0.02;
lon_sub(lon_sub == 360) = 360.02;

[lon_grid, lat_grid] = meshgrid(lon_sub, lat_sub);

ji = find(in);
if numel(lon_sub) == 1
    deps(ji) = interp1(lat_sub(:), z(:), latsq(ji));
elseif numel(lat_sub) == 1
    deps(ji) = interp1(lon_sub(:), z(:), lonsq(ji));
else
    deps(ji) = interp2(lon_grid, lat_grid, z', lonsq(ji), latsq(ji));
end

deps = reshape(deps, out_sz);
end