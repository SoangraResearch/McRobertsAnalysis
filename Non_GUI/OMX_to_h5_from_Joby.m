% read in data from omx file and convert it h5 format
clear;
clc;
addpath('DynaportCompany_Codes_new');

for i = 3:3
    si = num2str(i);
    filename=['/Users/minhaohuang/Desktop/Grad Assistant/Stroke_Raw_OMX_Files/CK',si,'/DATA0000'];            
    path=[filename,'.OMX'];   %filename to read 
    fileinfo = OMX_readFile(path,'info',1); % read the fileinfo
    fileinfo.start                 %print start time
    fileinfo.stop                  %print stop time
    rawData = OMX_readFile(path, ... 
              'packetInfo', fileinfo.packetInfo, ...
              'startTime', fileinfo.start.mtime, ... 
              'stopTime', fileinfo.stop.mtime,'modality',[1,1,0],'verbose',10);              
    %%
    MyData = soangraMoonResample( rawData ); 
    Dataset = ['/DS',num2str(i)]
    savefilename = ['/Users/minhaohuang/Desktop/Grad Assistant/Code_to_h5',si,'.h5']
    hdf5write(savefilename,Dataset,MyData)
    clear path ans  %prevent it to be saved
    
end
