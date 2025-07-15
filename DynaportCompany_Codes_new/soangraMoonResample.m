function MyData = soangraMoonResample( ourData )
%SOANGRAMOON Summary of this function goes here
%   
% % % USES findnearest.m function
% % % % % % % % % % Our Code Snippet
% % % % % % % % fileInfo = OMX_readFile(measFile,'info',1);
% % % % % % % % fileInfo.start
% % % % % % % % fileInfo.stop
% % % % % % % % ourData = OMX_readFile(measFile,'packetInfo',fileInfo.packetInfo,'startTime',fileInfo.start.mtime,...
% % % % % % % %                         'stopTime',fileInfo.stop.mtime,'modality',[1,1,0],'verbose',10);
% % % % % % % % 

% conversionGYR=[ourData.GYR(:,1) ourData.GYR(:,2:4)*0.07];

acc = ourData.ACC;
gyr = conversionGYR;

durAcc = acc(:,1)-acc(1,1);
durGyr = gyr(:,1)-acc(1,1);

durAcc = acc(:,1);
durGyr = gyr(:,1);

% Cut - synchronizing the Starting Time
if durAcc(1,1) > durGyr(1,1)
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

hz = datenum([0 0 0 0 0 0.010000]); %0.01 sec or 100 hz

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

OurTimeStamp =startIndex:hz:(startIndex+length(newAcc)*hz)-hz;

MyData =[OurTimeStamp',newAcc(1:end,2:4),newGyr(1:end,2:4)];
end

