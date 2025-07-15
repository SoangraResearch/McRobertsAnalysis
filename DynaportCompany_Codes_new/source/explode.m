function output = explode(delimiter, inputStr)
% Split a string at the location of the delimitter character into usefull chunks.
% 
% INPUT
%   delimitter  character at which point inputStr should be split (e.g. \t).
%   inputStr    string that should be split
%
% OUTPUT
%   output   an cell array of strings if inputStr contains alpha numeric data,
%            or a numeric collumn if inputStr contains numeric data as a
%            string. (example 1)
%
% EXAMPLES
%   explode(',','1,5,6,2,3,3,8,4')
%
%   explode(';', 'C:/hoi/doei;C:/hoi/lol')
%   explode(';', 'C:/hoi/doei;C:/hoi/lol;')
%   explode(';', ';C:/hoi/doei;C:/hoi/lol')
%   explode(';', ';')
%   explode(';', '')
%   explode(';', []) % crashes
%

% Date: 5-7-2016
% Author: s.frouws

assert(nargin==2,'explode:wrongnargin','Please provide two character input arguments.')
assert(ischar(inputStr) && ischar(delimiter),'explode:WrongInputFormat','The input is not a string. It is relatively a %s and a %s.',class(delimiter),class(inputStr))

% split the input string
split = regexp(inputStr,delimiter,'split');

if ~isempty(str2num(split{1}))
    
    % In the past, this error was not generated.
    assert(~any(cellfun(@(x) isempty(str2num(x)), split)),'explode:NotAllNummeric',...
        'The explode function tries to return the input string as a matrix, but not all splitted string parts seems to be numeric values.\n%s',inputStr(1:min([50 size(inputStr,2)])))
    
    output = str2num(str2mat(split));
    
else
    
    output = split;
    
end