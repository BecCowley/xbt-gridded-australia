function [temp,latitudes,longitudes,times,num_profiles,ti,transect_id] = check_transect_location(temp, latitudes,longitudes,times,num_profiles,ti,transect_id, transect, settings)
% Check the lats and lons arrays are within a defined polygon boundary.
% Remove the entire transect from the data if it does not meet the percent
% criteria
% input: temp, latitudes and longitudes matrices
%       transect label
% output:
%        temp, latitudes and longitudes matrices with lines outside the polygon removed
% Rebecca Cowley, Jan 2026


if isempty(settings)
    disp(['Polygon is not set up for transect ' transect_id ', using all data'])
    % use all the data
    return
else
    xp = settings.xp;
    yp = settings.yp;
end

% check the lats and longs for each transect to and keep those in the
% boundaries
irem = [];
for ind = 1:size(latitudes,2)
    tf = in_bounds(latitudes(:,ind),longitudes(:,ind),yp,xp,0.75);
    if ~tf 
        % remove this line from the data
        irem = [irem,ind];
    end
end
% remove the failed lines
temp(:,:,irem) = [];
latitudes(:,irem) = [];
longitudes(:,irem) = [];
times(:,irem) = [];
num_profiles(irem) = [];
transect_id(irem)=[];
ti(irem) = [];

end



function tf = in_bounds(lats,lons, boundary_lats, boundary_lons, x)
% function check_transect_location(location_matrix) 
% Check the lats and lons arrays are within a defined polygon boundary.
% Return True or False where more than x percent are within the boundary
% inputs:
%   lats: array of latitudes
%   lons: array of longitudes same size as latitudes
%   boundary_lats: 4 element vector of latitude boundaries
%   boundary_lons: 4 element vector of longitude boundaries
%   x: minimum percentage of points to accept, value between 0 and 1 (default 75%)

if nargin == 3
    x = 0.75;
end
if nargin < 3
    disp('3 input arguments are required')
    return
end
igood = ~isnan(lats.*lons);
% get the indices of points in the boundary
J = inpolygon(lons(igood), lats(igood),boundary_lons ,boundary_lats);

% get percentage
perc_in = sum(J)/length(lats(igood));

% More or less than acceptable?
if perc_in >= x
    tf = true;
else
    tf = false;
end
end