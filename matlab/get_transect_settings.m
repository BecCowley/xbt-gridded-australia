function settings = get_transect_settings(transect)
% get key settings for each transect used in gridding

% set up depending on transect
if strcmp('PX06',transect)
    orientation = 2; %North-south
    grid = -32.5:0.1:-20;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
    xp = [174.7 174.7 195 195];
    yp = [-16 -39 -39 -16];
elseif strcmp('PX05',transect)
    orientation = 2; %North-south
    grid = -26.65:0.1:29.26;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
    xp = [151 130 145 156];
    yp = [-27 30 30 -27];
elseif strcmp('PX03',transect)
    orientation = 2; %North-south
    grid = -26.65:0.1:29.26;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
    xp = [151 130 145 156];
    yp = [-27 30 30 -27];
elseif strcmp('PX30',transect)
    orientation = 1; %east-west
    grid = 153:0.1:178;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
    xp = [153 153 178.7 178.7];
    yp = [-27 -24.8 -15.7 -21.7 ];
elseif strcmp('PX34',transect)
    orientation = 1;
    grid = 151.2:0.1:173;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
    xp = [151.3 151.3 174 174];
    yp = [-35 -33.8 -38.8 -41.2];
elseif strcmp('PX32',transect)
    orientation = 1;
    grid = 151.2:0.1:172.4;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
    xp = [150.8 150.8 173 173];
    yp = [-35 -31.5 -31.5 -35];
elseif strcmp('IX28', transect)
    orientation = 2; %North-south
    grid = -66.5:0.1:-43.5;
    gaps = 2;
    e1 = 40; % 40 stations for high resolution
    xp = [135.0 140.5 150.2 149];
    yp = [-66.5 -40 -40 -66.5];   
elseif strcmp('IX01',transect) || strcmp('IX1',transect)
    orientation = 2; %North-south
    grid = -35:0.5:-5;
    gaps = 6;
    e1 = 20; % 40 stations for frequently repeated
    xp = [112.0 102 108.5 116];
    yp = [-35 -5 -5 -27];
elseif strcmp('IX22-PX11',transect) || strcmp('IX22',transect)
    orientation = 2; %North-south
    grid = -20.9:0.5:29.26;
    gaps = 4;
    e1 = 20; % 40 stations for frequently repeated
    xp = [116.0 123.4 124 124.6 135.83 129.5 127.7 120.35];
    yp = [-19.7 -7 -3 20.5 20.5 -3 -7 -19.7];  
elseif strcmp('PX02',transect) || strcmp('PX2',transect)
    orientation = 1; %east-west
    grid = 114.7:0.5:135.2;
    gaps = 4;
    e1 = 20; % 40 stations for frequently repeated
    xp = [114.5 114.5 135 135];
    yp = [-8 -5 -8.5 -10.75 ];
elseif strcmp('IX12',transect)
    orientation = 1; %East-west
    grid = 50:0.5:116;
    gaps = 4;
    e1 = 20; % 40 stations for frequently repeated
    xp = [50 50 116 116];
    yp = [7 18 -30.5 -35.5];
elseif strcmp('IX15', transect)
    orientation = 1;
    grid = 57.5:0.5:116;
    gaps = 4;
    e1 = 20;
    xp = [50 50 116 116];
    yp = [-22.5 -17.7 -30.5 -35.5];
elseif strcmp('IX31', transect)%needs checking
    orientation = 1;
    grid = 116:0.5:143;
    gaps = 4;
    e1 = 20;
    xp = [116 116 143 143];
    yp = [-45 -42 -42 -45];  
elseif strcmp('IX02', transect)
    orientation = 1;
    grid = 31.3:0.5:116;
    gaps = 4;
    e1 = 20;
    xp = [31 31 116 116];
    yp = [-39 -33 -33 -39];      
elseif strcmp('IX21', transect)
    orientation = 1;
    grid = 31.3:0.5:58;
    gaps = 4;
    e1 = 20;
    xp = [31 31 58 58];
    yp = [-31 -19 -19 -31];  
elseif strcmp('IX06', transect) % needs refining
    orientation = 1;
    grid = 58:0.5:110;
    gaps = 4;
    e1 = 20;
    xp = [58 58 110 110];
    yp = [-31 10 10 -31];  
else
    disp(['transect argument is not coded in yet for ' transect])
    settings = [];
    return
end

settings.orientation = orientation;
settings.grid = grid;
settings.gaps = gaps;
settings.e1 = e1;
settings.xp = xp;
settings.yp = yp;

