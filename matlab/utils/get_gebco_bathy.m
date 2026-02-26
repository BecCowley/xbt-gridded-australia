function deps = get_gebco_bathy(fnm, lats,lons)
% get the bathymetry from the gebco gridded bathy dataset
% inputs:
%   lats = latitudes of locations to retrieve
%   lons = longitudes of locations to retrieve
%   Gebco file path is hard coded in.
% Bec Cowley, October, 2025

% Find the indices of lat/lon range
desired_lat_range = [min(lats) max(lats)]; 
desired_lon_range = [min(lons) max(lons)];

% pre-allocate deps
deps = nan(size(lons));
ii = 1:numel(lons);
try
    lat = ncread(fnm, 'latitude');
    lon = ncread(fnm, 'longitude');
catch
    lat = ncread(fnm, 'lat');
    lon = ncread(fnm, 'lon');
end
% while loop
while ~isempty(ii)
    jj = find(lons(ii)>=min(lon) & lons(ii)<=max(lon) & lats(ii)>=min(lat) & lats(ii)<=max(lat));
    ji = ii(jj);

    if ~isempty(ji)
  	  % Broaden region slightly (by .1 degree) so extracted chunk encloses
      % all points
      ix = find(lon>=min(lons(ji))-.1 & lon<=max(lons(ji))+.1);
      iy = find(lat>=min(lats(ji))-.1 & lat<=max(lats(ji))+.1);
      % now interpolate to return the information along this line
      lon(lon==0) = -.02;    % Enable interpolation to x=0
      lon(lon==360) = 360.02;    % Enable interpolation to x=360
      % read the heights
      try
        heights = ncread(fnm,'height',[ix(1) iy(1)],[ix(end)-ix(1)+1 iy(end)-iy(1)+1]);
      catch
        heights = double(ncread(fnm,'elevation',[ix(1) iy(1)],[ix(end)-ix(1)+1 iy(end)-iy(1)+1]));
      end

      [lon,lat] = meshgrid(lon(ix),lat(iy));
      if length(ix)==1
          % Degenerate case where only want points on boundary of dataset
          deps(ji) = interp1(lat,heights,lats(ji));
      elseif length(iy)==1
          % Ditto
          deps(ji) = interp1(lon,heights,lons(ji));
      else
          deps(ji) = interp2(lon,lat,heights',lons(ji),lats(ji));
      end

      % Remove from the list only points for which we have obtained data.
      ll = find(~isnan(deps(ii(jj))));
      ii(jj(ll)) = [];
    else
        ii = [];
    end
end