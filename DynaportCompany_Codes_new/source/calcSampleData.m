function signal = calcSampleData(data,mark)
% function signal = calcSampleData(data,mark)
% Converts the timestamp data to sample data according to the old DynaPort
%
% INPUT
%   data:     contains accelerometer and gyroscope data with timestamps
%   mark:     contains marker numbers with timestamps
%
% OUTPUT
%   signal: 100 Hz signal [acc CC,acc ML,acc AP,gyr CC,gyr ML,gyr AP,mark]
%

acc = data.ACC;
gyr = data.GYR;

durAcc = acc(:,1)-acc(1,1);
durGyr = gyr(:,1)-acc(1,1);

% Cut
if durAcc(1,1) > durGyr(1,1);
    startIndex = durAcc(1,1);
    temp = findnearest(startIndex,durGyr);
    durGyr = durGyr(temp:end,:);
    gyr = gyr(temp:end,:);
else
    startIndex = durGyr(1,1);
    temp = findnearest(startIndex,durAcc);
    durAcc = durAcc(temp:end,:);
    acc = acc(temp:end,:);
end

durAcc = durAcc(:,1) - durAcc(1,1);
durGyr = durGyr(:,1) - durGyr(1,1);

hz = datenum([0 0 0 0 0 0.010000]);

% interpolate
newAcc=interp1(durAcc',...
    acc,...
    0:hz:durAcc(end,1),'linear');

newGyr=interp1(durGyr',...
    gyr,...
    0:hz:durGyr(end,1),'linear');

if size(newGyr,1) > size(newAcc,1)
    newGyr = newGyr(1:size(newAcc,1),:);
else
    newAcc = newAcc(1:size(newGyr,1),:);
end

% adding markers
signal = [newAcc newGyr(:,2:4)];
signal(:,8) = zeros(size(signal,1),1);
if ~isempty(mark)
    for iF = 1:size(mark,1)
        temp = findnearest(mark(iF,1),signal(:,1));
        signal(temp,8) = mark(iF,2);
    end
end

% adding length of the test if available (for gait and 6mw)
signal(:,9) = zeros(size(signal,1),1);
if size(mark,2) == 3
    for iF = 1:size(mark,1)
        temp = findnearest(mark(iF,1),signal(:,1));
        signal(temp,9) = mark(iF,3);
    end
end

signal = signal(:,2:9);
signal(isnan(signal(:,8)),8) = 0;

% Adapting the signal to the Hybrid style
signal = [-signal(:,2) signal(:,1) signal(:,3) -signal(:,5) signal(:,4) signal(:,6) signal(:,7) signal(:,8)];
signal(:,4:6) = signal(:,4:6).*0.07;
