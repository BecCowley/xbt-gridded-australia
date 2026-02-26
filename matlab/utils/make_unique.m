function arr_unique = make_unique(arr)
% MAKE_UNIQUE Ensures all values in arr are unique by adding a small factor to duplicates.
% arr: input array (vector)
% arr_unique: output array with unique values in the original order


arr_unique = arr;                % Copy to preserve order
[uarr,~,ic] = unique(arr);          % Map original values to unique indices
%loop until unique
while length(arr) > length(uarr)    counts = accumarray(ic(:),1);    % Count instances of each unique value
    epsilon = 1e-4;                 % Small factor to add
    
    for i = 1:numel(arr)
        idx = ic(i);
        if counts(idx) > 1           % If value occurs more than once
            % Find which occurrence this is
            prev_occurrences = find(arr(1:i-1)==arr(i));
            arr_unique(i) = arr(i) + epsilon * numel(prev_occurrences);
        end
    end
    % recheck for uniqueness
    arr = arr_unique;  
    [uarr,~,ic] = unique(arr);   
end