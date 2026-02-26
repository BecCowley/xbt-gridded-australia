function combine_transects(out_data_dir,transect)
% combine some transects for specific collections
% and remove data with bad data still at AODN. Will need updating when data
% files are fixed at AODN.
% Bec Cowley 12 Feb, 2026

if contains('PX30',transect)
    % combine PX30-31-200107-1 and PX30-31-200107-2
    load([out_data_dir '/PX30-31-200107-4.mat']);
    xbt_2 = xbt;
    load([out_data_dir '/PX30-31-200107-1.mat']);

    % concatenate
    xbt.TIME = [xbt.TIME;xbt_2.TIME];
    xbt.LONGITUDE  = [xbt.LONGITUDE; xbt_2.LONGITUDE];
    xbt.LATITUDE = [xbt.LATITUDE; xbt_2.LATITUDE];
    xbt.TEMP = [xbt.TEMP, xbt_2.TEMP];
    % regrid
    xbt = grid_simple(xbt,transect);
    % save the new structure
    save([out_data_dir '/PX30-31-200107-1.mat'],'xbt');
    % remove the other
    delete([out_data_dir '/PX30-31-200107-4.mat']);

    % remove the others
    delete([out_data_dir '/PX30-31-200509-2.mat']);
    delete([out_data_dir '/PX30-31-200509-3.mat']);
    delete([out_data_dir '/PX30-31-200003-3.mat']);
    delete([out_data_dir '/PX30-31-202301-1.mat']);    
end

if contains('PX32_34',transect)
    % combine PX34-200901-1 and PX34-200901-3    load('PX30-31-200107-2.mat');
    load([out_data_dir '/PX34-200901-3.mat']);
    xbt_2 = xbt;
    load([out_data_dir '/PX34-200901-1.mat']);

    % concatenate
    xbt.TIME = [xbt.TIME;xbt_2.TIME];
    xbt.LONGITUDE  = [xbt.LONGITUDE; xbt_2.LONGITUDE];
    xbt.LATITUDE = [xbt.LATITUDE; xbt_2.LATITUDE];
    xbt.TEMP = [xbt.TEMP, xbt_2.TEMP];
    % regrid
    xbt = grid_simple(xbt,transect);
    % save the new structure
    save([out_data_dir '/PX34-200901-1.mat'],'xbt');
    % remove the other
    delete([out_data_dir '/PX34-200901-3.mat']);
end

if contains('PX02',transect)
    
    % remove some whole transects
    delete([out_data_dir '/PX2-200806-2.mat']); 
end


if contains('IX22-PX11',transect)
    
    % remove some whole transects
    delete([out_data_dir '/IX22-PX11-199907-1.mat']); 
    delete([out_data_dir '/IX22-PX11-200305-1.mat']); 
    delete([out_data_dir '/IX22-PX11-200502-1.mat']); 
    delete([out_data_dir '/IX22-PX11-200801-1.mat']); 
    delete([out_data_dir '/IX22-PX11-201002-2.mat']); 
    delete([out_data_dir '/IX22-PX11-201712-3.mat']); 

end
