function output = removeRows(input, rowNrs)
% remove a specified rows from the input data
%
% INPUT
%   input*   matrix from which data should be removed
%   rowNrs*  array of row numbers to remove or a logical array
%
% OUTPUT
%   output  matrix with rows "rowNrs" removed.

% TODO: this function should replace removeRow

keep = true(size(input,1),1);
keep(rowNrs,1) = false;
output = input(keep,:);
