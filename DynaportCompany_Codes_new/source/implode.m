function output=implode(delimiter, array, quoteChar)
% Join array elements in a delimited string
%
% INPUT
%   delimitter  character at which point the input string should be split (e.g. \t).
%   array       matrix or cell array (nx1) with elements that should be stuck together
%   quoteChar   character used as quote can be one of ('"' '''' '`' '')
%   default is ''
%
% OUTPUT
%   output   string, containing all the array elements, delimited by delimiter
%
% NOTE
% This function does exactly the same as its php-equivalent (http://nl2.php.net/implode)

% check array size, must be a column or row vector
if nargin<3
    quoteChar = '';
end

assert(min(size(array))==1,'Input must a Mx1 or 1xN vector')
assert(ismember(quoteChar,{'"','''','`',''}),'quoteChar must be one of {''"''} {''''''''} {''`''} {''''}')

if size(array,1) == 1
    array = array';
end

output=[];

if iscell(array)
    % start with some quotes because we're outputting a string
    output = quoteChar;
    for i=1:size(array,1)
        output=[output array{i,1} quoteChar delimiter quoteChar];
    end
    if strcmp(output(end),delimiter)
        output=output(1:end-1);
    elseif ~strcmp(quoteChar,'') && strcmp(output(end),quoteChar)
        output=output(1:end-2);        
    end
    output = deblank(output);
else
    for i=1:size(array,1)
        output=[output num2str(array(i,1)) '' delimiter ''];
    end
    output=num2str(output(1:end-size(delimiter,2)));
end