% dynaportOmxRead - Reads raw timestamped data from measurement file
% and maps it to a time axis of exactly 100 Hz
%
% Syntax:  [measurementInfo,sig] = dynaportOmxRead(measFile)
%
% Inputs:
%    measFile - string with file name of the measurement file
%
% Outputs:
%    measurementInfo - struct containing info about the measurement
%    sig - nx6 matrix containing signal data and marker data mapped to a
%          time series of exactly 100 Hz in the following format:
%          sig = [a_v,a_ml,a_ap,g_yaw,g_pitch,g_roll,markerIds]
%   measurementInfo - struct containing th efollowing fields:
%       - markers nx4 matrix containing information about the markers in
%       the file in th efollowing format: [start sample, end sample, marker id, distance]
%
%
%
% Author: Erik Ainsworth
% Created: May 2014