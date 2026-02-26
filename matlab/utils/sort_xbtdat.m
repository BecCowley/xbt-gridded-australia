% function xbt = sort_xbtdat(xbt,bath)
% originally from sort_xbtdat, Ken Ridgway. 
% Renamed to be more descriptive of what the code does. Rebecca Cowley,
% 2025
% 1. Sort the data and ensure the key axis is monotonic.
% 
% Inputs:
%   xbt: structure with temperature matrix, depth, lat, long for one transect
%   bath: bathymetry for the data at locations xbt.LATITUDE, xbt.LONGITUDE
%   orientation: main orientation of the line, 1 = LONGITUDE, 2 = LATITUDE
%
% Outputs:
%   xbt structure sorted and cleaned.
%   matching bathymetry for each remaining and sorted profile location

function [xbt, bath] = sort_xbtdat(xbt,bath, orientation)

% first ensure the lat or lon is sorted and monotonic
if orientation == 1
    % sort the castx by lon
    [xbt.LONGITUDE,I] = sort(xbt.LONGITUDE);
    % update the xbt variables to match the sorting
    xbt.LATITUDE = xbt.LATITUDE(I);
    % make monotonic
    xbt.LONGITUDE = make_unique(xbt.LONGITUDE);
else
    % sort the castx by lon
    [xbt.LATITUDE,I] = sort(xbt.LATITUDE);
    % update the xbt variables to match the sorting
    xbt.LONGITUDE = xbt.LONGITUDE(I);
    % make monotonic
    xbt.LATITUDE = make_unique(xbt.LATITUDE);    % sort by lat
end
% update the xbt variables to match the sorting
xbt.TIME = xbt.TIME(I);
xbt.TEMP = xbt.TEMP(:,I);
bath = bath(I);











