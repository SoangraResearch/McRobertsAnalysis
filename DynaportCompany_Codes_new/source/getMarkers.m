function markers = getMarkers(fn, markers, startTimeStamp)


if ~isempty(markers) && ~strcmpi(markers,'[]') && isfield(cell2mat(loadjson(markers)),'marker')
    
    % JSON METHOD
    data = cell2mat(loadjson(markers));
    markers = cell(size(data,2),5);
    for iF = 1:size(data,2)
        markers{iF,1} = data(iF).trial;
        markers{iF,2} = data(iF).marker;
        markers{iF,3} = (data(iF).xaxis.from/60/60/24) + startTimeStamp;
        markers{iF,4} = (data(iF).xaxis.to/60/60/24) + startTimeStamp;
        if isfield(data,'setting') && ~isempty(data(iF).setting)
            markers{iF,5} = data(iF).setting;
        else
            markers{iF,5} = nan;
        end
    end
    
    markers = [cell2mat(markers(:,3)),str2num(cell2mat(markers(:,2))),cell2mat(markers(:,5))...
        ;cell2mat(markers(:,4)),str2num(cell2mat(markers(:,2))),cell2mat(markers(:,5))];
    
else
    
    % OLD METHOD
    if isdeployed
        prog = [getCurrentPath(), '\convert.exe'];
    else
        prog = which('convert.exe');
    end
    [status,res] = dos(strcat(prog ,' "',fn,'"  -t:matlab -stream *'));
    pos = strfind(res,'CONVERT');
    result = res(1:pos-1);
    if ~isempty(result)
        if ~isempty(strfind(result,'ts'))
            temp = strfind(result,'"');
            markers = nan(size(temp,2)/2,3);
            count = 1;
            for iString = 1:2:size(temp,2)-1
                marker = result(temp(iString)+1:temp(iString+1)-1);
                marker = explode(';',marker);
                for iMarker = 1:size(marker,2)
                    mark = explode(',',marker{iMarker});
                    switch mark{1}
                        case 'ts'
                            markers(count,1) =  datenum(unixtime(str2num(mark{2})/1000));
                        case 'id'
                            markers(count,2) = str2num(mark{2});
                        case 'dist'
                            if ~isempty(mark{2})
                                markers(count,3) = str2num(mark{2});
                            end
                    end
                end
                count = count + 1;
            end
        else
            if ~isempty(strfind(result,' '))
                formatStr = '%s%s%s';
                result = strrep(strrep(result,' ','","'),'"','');
                temp = textscan(result,formatStr,'Delimiter',',');
                markers2(:,1) = str2double(temp{1});
                markers2(:,2) = str2double(temp{2});
                markers2(:,3) = str2double(temp{3});
            else
                formatStr = '%s%s';
                temp = textscan(result,formatStr,'Delimiter',',');
                markers2 = str2double(temp{1});
                for iM = 1:size(temp{1},1)
                    % sometimes random characters are added to the output so we should only select numeric data
                    markers2(iM,2) = str2double(temp{2}{iM}(regexp(temp{2}{iM},'\d')));
                end
            end
            markers = markers2;
        end
        markers = removeRows(markers,find(markers(:,2) == 2 | markers(:,2) == -2));
    else
        markers = [];
    end
    
end
