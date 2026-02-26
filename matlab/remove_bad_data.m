function xbt = remove_bad_data(xbt, transect)
% remove specific profiles that contain bad data at the AODN. Update when
% the profiles are replaced.

if contains('PX30',transect)
    if contains(xbt.atts.transect_id,'199904-2')
        % remove this entire cruise, part of franklin voyage that isn't on
        % line
        xbt = [];
        return
    end

    if contains(xbt.atts.transect_id, '200003-2')
        % remove eastern half as not on transect
        ibad = xbt.LONGITUDE > 167.3;
        xbt.TIME(ibad) = [];
        xbt.LONGITUDE(ibad) = [];
        xbt.LATITUDE(ibad) = [];
        xbt.TEMP(:,ibad) = [];
        return
    end

    if contains(xbt.atts.transect_id, '200107-1')
        % profiles 108,111 have wirebreaks missed
        ibad = [108,111];
        xbt.TIME(ibad) = [];
        xbt.LONGITUDE(ibad) = [];
        xbt.LATITUDE(ibad) = [];
        xbt.TEMP(:,ibad) = [];
        return
    end
    
    if contains(xbt.atts.transect_id, '200403-1')
        % profile 98 have wirebreaks missed
        ibad = 98;
        xbt.TIME(ibad) = [];
        xbt.LONGITUDE(ibad) = [];
        xbt.LATITUDE(ibad) = [];
        xbt.TEMP(:,ibad) = [];
        return
    end        

    if contains(xbt.atts.transect_id,'200609-1')
        % remove this entire cruise, still has bad data
        xbt = [];
        return
    end
    if contains(xbt.atts.transect_id, '200711-1')
        % profile 100 have wirebreaks missed
        ibad = 100;
        xbt.TIME(ibad) = [];
        xbt.LONGITUDE(ibad) = [];
        xbt.LATITUDE(ibad) = [];
        xbt.TEMP(:,ibad) = [];
        return
    end  
end
%%

if contains('PX34', transect) | contains('PX32', transect)
    % remove all data east of 173 and south of 41
    ibad = xbt.LONGITUDE > 173 & xbt.LATITUDE < -41;
    xbt.TIME(ibad) = [];
    xbt.LONGITUDE(ibad) = [];
    xbt.LATITUDE(ibad) = [];
    xbt.TEMP(:,ibad) = [];
    
    if contains(xbt.atts.transect_id,'200802-1')
        % remove wire break profile
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,59) = NaN;
        idep = xbt.DEPTH > 270;
        xbt.TEMP(idep,2) = NaN;
        return
    end
    % remove some identified bad data
    if contains(xbt.atts.transect_id,'200008-1')
        idep = xbt.DEPTH > 540;
        xbt.TEMP(idep,11) = NaN;
        return
    end


    if contains(xbt.atts.transect_id, '200105-1')
        idep = xbt.DEPTH > 460;
        xbt.TEMP(idep,25) = NaN;
        return
    end

end
%%
if contains('PX02',transect)
    % remove some identified bad data
    if contains(xbt.atts.transect_id, '202008-1')
        idep = xbt.DEPTH > 340;
        xbt.TEMP(idep,16) = NaN;
        return
    end

    %next
    if contains(xbt.atts.transect_id, '200008-1')
        idep = xbt.DEPTH > 780;
        xbt.TEMP(idep,7) = NaN;
        return
    end
    %next
    if contains(xbt.atts.transect_id, '200810-2')
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,13) = NaN;
        return
    end

    %next
    if contains(xbt.atts.transect_id, '200811-1')
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,12:end) = NaN;
        return
    end

    %next
    if contains(xbt.atts.transect_id, '201104-1')
        idep = xbt.DEPTH > 200;
        xbt.TEMP(idep,16) = NaN;
        return
    end


end
%%
if contains('IX28',transect)
    % remove some identified bad data
    if contains(xbt.atts.transect_id, '199801-2')
        idep = xbt.DEPTH > 900;
        xbt.TEMP(idep,79) = NaN;
        return
    end

    %next
    if contains(xbt.atts.transect_id, '199911-1')
        idep = xbt.DEPTH > 890;
        xbt.TEMP(idep,14) = NaN;
        return
    end
    %next
    if contains(xbt.atts.transect_id, '200202-1')
        idep = xbt.DEPTH > 50;
        xbt.TEMP(idep,21) = NaN;
        return
    end

    %next
    if contains(xbt.atts.transect_id, '200402-1')
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,17) = NaN;
        return
    end
    %next
    if contains(xbt.atts.transect_id, '200612-1')
        idep = xbt.DEPTH > 860;
        xbt.TEMP(idep,36) = NaN;
        idep = xbt.DEPTH > 880;
        xbt.TEMP(idep,48) = NaN;
        idep = xbt.DEPTH > 880;
        xbt.TEMP(idep,51) = NaN;
        idep = xbt.DEPTH > 770;
        xbt.TEMP(idep,64) = NaN;
        idep = xbt.DEPTH > 680;
        xbt.TEMP(idep,[77,78]) = NaN;
        return
    end

    %next
    if contains(xbt.atts.transect_id, '200701-1')
        idep = xbt.DEPTH > 860;
        xbt.TEMP(idep,14) = NaN;
        idep = xbt.DEPTH > 800;
        xbt.TEMP(idep,15) = NaN;
        idep = xbt.DEPTH > 760;
        xbt.TEMP(idep,46) = NaN;
        idep = xbt.DEPTH > 30;
        xbt.TEMP(idep,9) = NaN;
        idep = xbt.DEPTH > 100;
        xbt.TEMP(idep,44) = NaN;
        return
    end    % regrid


    %next
    if contains(xbt.atts.transect_id, '200702-1.mat')
        idep = xbt.DEPTH > 490;
        xbt.TEMP(idep,19) = NaN;
        return
    end

    %next
    if contains(xbt.atts.transect_id, 'IX28-200802-1')
        idep = xbt.DEPTH > 190;
        xbt.TEMP(idep,5) = NaN;
        idep = xbt.DEPTH > 300;
        xbt.TEMP(idep,6) = NaN;
        idep = xbt.DEPTH > 700;
        xbt.TEMP(idep,9) = NaN;
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,[9,23,69,75,79]) = NaN;
        idep = xbt.DEPTH > 40;
        xbt.TEMP(idep,30) = NaN;
        idep = xbt.DEPTH > 690;
        xbt.TEMP(idep,67) = NaN;
        idep = xbt.DEPTH > 470;
        xbt.TEMP(idep,75) = NaN;
        idep = xbt.DEPTH > 810;
        xbt.TEMP(idep,79) = NaN;
        return
    end

    %next
    if contains(xbt.atts.transect_id, '200802-1')
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,[8,15,32,33,34,37,39]) = NaN;
        return
    end

    %next
    if contains(xbt.atts.transect_id, '200812-1')
        idep = xbt.DEPTH > 650;
        xbt.TEMP(idep,31) = NaN;
        return
    end


    %next
    if contains(xbt.atts.transect_id, '201002-1')
        idep = xbt.DEPTH > 770;
        xbt.TEMP(idep,34) = NaN;

        return
    end

    %next
    if contains(xbt.atts.transect_id, '201012-2')
        idep = xbt.DEPTH > 910;
        xbt.TEMP(idep,100) = NaN;
        idep = xbt.DEPTH > 890;
        xbt.TEMP(idep,97) = NaN;
        idep = xbt.DEPTH > 470;
        xbt.TEMP(idep,89) = NaN;
        return
    end

    %next
    if contains(xbt.atts.transect_id, '201212-3')
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,60) = NaN;
        return
    end
    %next
    if contains(xbt.atts.transect_id, '201802-3')
        idep = xbt.DEPTH > 430;
        xbt.TEMP(idep,28) = NaN;
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,35) = NaN;
        return
    end


end
%%
if contains('IX22-PX11',transect)
    % remove some identified bad data
    if contains(xbt.atts.transect_id, '199907-1')
        idep = xbt.DEPTH > 870;
        xbt.TEMP(idep,[41,42]) = NaN;
        idep = xbt.DEPTH > 820;
        xbt.TEMP(idep,13) = NaN; 
        return
    end
    % remove some identified bad data
    if contains(xbt.atts.transect_id, '200706-1')
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,[23,24,29,33,46]) = NaN;
        idep = xbt.DEPTH > 870;
        xbt.TEMP(idep,26) = NaN;
        return
    end
    if contains(xbt.atts.transect_id, '201204-1')
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,21) = NaN;
        return
    end
    if contains(xbt.atts.transect_id, '201611-2')
        idep = xbt.DEPTH > 860;
        xbt.TEMP(idep,22) = NaN;
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,15) = NaN;
        return
    end    
end



%%
if contains('IX01',transect)
    % remove some identified bad data
    if contains(xbt.atts.transect_id, '199805-2')
        idep = xbt.DEPTH > 870;
        xbt.TEMP(idep,13) = NaN;
        return
    end

    % remove some identified bad data
    if contains(xbt.atts.transect_id, '200810-1')
        idep = xbt.DEPTH > 730;
        xbt.TEMP(idep,2) = NaN;
        return
    end

    if contains(xbt.atts.transect_id, '200901-2')
        idep = xbt.DEPTH > 0;
        xbt.TEMP(idep,4) = NaN;
        return
    end
    if contains(xbt.atts.transect_id, '201312-4')
        idep = xbt.DEPTH > 310;
        xbt.TEMP(idep,6) = NaN;
        return
    end


end