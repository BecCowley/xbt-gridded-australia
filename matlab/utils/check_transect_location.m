function [temp,latitudes,longitudes,ti,num_profiles,transect_id] = check_transect_location(temp, latitudes,longitudes,ti,num_profiles,transect_id, transect)
% Check the lats and lons arrays are within a defined polygon boundary.
% Remove the entire transect from the data if it does not meet the percent
% criteria
% input: temp, latitudes and longitudes matrices
%       transect label
% output:
%        temp, latitudes and longitudes matrices with lines outside the polygon removed
% Rebecca Cowley, Jan 2026


if contains('PX06', transect)
    % PX06
    xp = [174.7 174.7 195 195];
    yp = [-16 -39 -39 -16];
elseif contains('PX30',transect)
    % PX30
    xp = [153 153 178.7 178.7];
    yp = [-27 -24.8 -15.7 -21.7 ];
elseif contains('PX34',transect)
    % PX34
    xp = [151.3 151.3 174 174];
    yp = [-35 -33.8 -38.8 -41.2];
elseif contains('PX32',transect)
    % TODO: PX32 - need to refine this or combine with PX34
    xp = [150.8 150.8 173 173];
    yp = [-35 -31.5 -31.5 -35];
elseif contains('IX28', transect)
    xp = [135.0 140.5 150.2 149];
    yp = [-66.5 -40 -40 -66.5];   
elseif contains('IX01', transect)
    xp = [112.0 102 108.5 116];
    yp = [-35 -5 -5 -27];  
elseif contains('IX22-PX11', transect)
    xp = [116.0 123.4 124 124.6 135.83 129.5 127.7 120.35];
    yp = [-19.7 -7 -3 20.5 20.5 -3 -7 -19.7];  
elseif contains('PX02',transect)
    % PX02
    xp = [114.5 114.5 135 135];
    yp = [-8 -5 -8.5 -10.75 ];
elseif contains('IX12',transect)
    % IX12
    xp = [112 112 116 116];
    yp = [7 18 -30.5 -35.5];
else
    disp('transect argument must be one of ''PX30'',''PX34'',''PX06'',''PX32'',''IX01''')
    return
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
ti(irem) = [];
num_profiles(irem) = [];
transect_id(irem)=[];

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