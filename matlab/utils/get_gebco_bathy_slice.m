function bathy = get_gebco_bathy_slice(fnm, lats, lons)
% read the GEBCO bathymetry slice needed to cover the requested lat/lon range
% inputs:
%   fnm  = NetCDF filename
%   lats = latitudes defining the requested region
%   lons = longitudes defining the requested region
% output:
%   bathy = struct containing:
%       bathy.z   = bathymetry values
%       bathy.lat = latitude vector for the slice
%       bathy.lon = longitude vector for the slice
% Bec Cowley, October, 2025

bathy = struct('lat', [], 'lon', [], 'z', []);

if isempty(lats) || isempty(lons)
    return
end

persistent meta
if isempty(meta) || ~isfield(meta, 'fnm') || ~strcmp(meta.fnm, fnm)
    meta = local_read_meta(fnm);
end

lats = double(lats(:));
lons = double(lons(:));

% Match longitude convention to file
if meta.lon_is_360
    lons(lons < 0) = lons(lons < 0) + 360;
else
    lons(lons > 180) = lons(lons > 180) - 360;
end

% Requested bounding box
pad = 0.1;
minLat = min(lats) - pad;
maxLat = max(lats) + pad;
minLon = min(lons) - pad;
maxLon = max(lons) + pad;

% Clip to dataset extent
minLat = max(minLat, meta.lat_min);
maxLat = min(maxLat, meta.lat_max);
minLon = max(minLon, meta.lon_min);
maxLon = min(maxLon, meta.lon_max);

if minLat > maxLat || minLon > maxLon
    return
end

% Convert requested bounds directly to index bounds
ix = sort([ ...
    floor((minLon - meta.lon_first) / meta.dlon) + 1, ...
    ceil((maxLon - meta.lon_first) / meta.dlon) + 1]);
iy = sort([ ...
    floor((minLat - meta.lat_first) / meta.dlat) + 1, ...
    ceil((maxLat - meta.lat_first) / meta.dlat) + 1]);

ix1 = max(1, ix(1));
ix2 = min(meta.nlon, ix(2));
iy1 = max(1, iy(1));
iy2 = min(meta.nlat, iy(2));

if ix1 > ix2 || iy1 > iy2
    return
end

bathy.z = double(ncread(fnm, meta.z_name, [ix1 iy1], [ix2 - ix1 + 1, iy2 - iy1 + 1]));
bathy.lon = meta.lon_first + ((ix1:ix2) - 1) * meta.dlon;
bathy.lat = meta.lat_first + ((iy1:iy2) - 1) * meta.dlat;

end

function meta = local_read_meta(fnm)
try
    ncread(fnm, 'latitude', 1, 1);
    meta.lat_name = 'latitude';
    meta.lon_name = 'longitude';
catch
    meta.lat_name = 'lat';
    meta.lon_name = 'lon';
end

try
    info = ncinfo(fnm, 'height');
    meta.z_name = 'height';
catch
    info = ncinfo(fnm, 'elevation');
    meta.z_name = 'elevation';
end

lat2 = double(ncread(fnm, meta.lat_name, 1, 2));
lon2 = double(ncread(fnm, meta.lon_name, 1, 2));

meta.lat_first = lat2(1);
meta.lon_first = lon2(1);
meta.dlat = lat2(2) - lat2(1);
meta.dlon = lon2(2) - lon2(1);

meta.nlon = info.Size(1);
meta.nlat = info.Size(2);

meta.lat_last = meta.lat_first + (meta.nlat - 1) * meta.dlat;
meta.lon_last = meta.lon_first + (meta.nlon - 1) * meta.dlon;
meta.lat_min = min(meta.lat_first, meta.lat_last);
meta.lat_max = max(meta.lat_first, meta.lat_last);
meta.lon_min = min(meta.lon_first, meta.lon_last);
meta.lon_max = max(meta.lon_first, meta.lon_last);

meta.lon_is_360 = meta.lon_min >= 0 && meta.lon_max > 180;
meta.fnm = fnm;
end