function [measInfo,sig] = dynaportOmxRead(measFile)
% dynaportOmxRead - Reads raw timestamped data from measurement file
% and maps it to a time axis of exactly 100 Hz
%
% Syntax:  [measurementInfo,sig] = dynaportOmxRead(measFile,xmltree)
%
% Inputs:
%    measFile - string with file name of the measurement file
%    xmltree - struct with information about measurement request.
%              The value of this may be []
%
% Outputs:
%    measurementInfo - struct containing info about the measurement
%    sig - nx7 matrix containing signal data and marker data mapped to a
%          time series of exactly 100 Hz in the following format:
%          sig = [a_v,a_ml,a_ap,g_yaw,g_pitch,g_roll,markerIds]
%
% Example:
%
%
% Other m-files required: none
% Subfunctions: none
% MAT-files required: none
%
% See also: OTHER_FUNCTION_NAME1,  OTHER_FUNCTION_NAME2
%
% Author: Erik Ainsworth
% Created: May 2014

%read measurement info (e.g. serial number, start timestamp, end timestamp)
% measurementInfo = OMX_readFile(measFile,'info',1);

% read raw time stamped data for accelerometer and gyroscope and (no magnetometer)

MTdata = OMX_readFile(measFile,'modality', [1, 1, 0]);
measInfo.metadata = getMetaData(measFile);
startTime = datenum(unixtime(str2num(measInfo.metadata.firstTimestamp)));
markers = getMarkers(measFile,[], startTime);

sig = calcSampleData(MTdata,markers);
intervals = createMarkerIntervals(sig(:,7));
                
intervals(:,4) = nan(size(intervals,1),1);
gaitLength = createMarkerIntervals(sig(:,8));
if ~isempty(gaitLength)
    for iGait = 1:size(gaitLength,1)
        ind = (gaitLength(iGait,1) == intervals(:,1)) & (gaitLength(iGait,2) == intervals(:,2));
        intervals(ind,4) = gaitLength(iGait,3);
    end
end

sig = sig(:,1:6);
measInfo.markers = intervals;
