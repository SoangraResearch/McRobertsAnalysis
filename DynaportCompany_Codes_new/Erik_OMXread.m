data = OMX_readFile('C:\matlab_code\mcroberts\REU_DATA_ALL\REU_Dynaport data\AAA0009_good_4day\Gab_24hour.OMX','modality',[1 1 0]);
 ind = [592524,592525,592526,592527,592528,592529]
 datestr(data.GYR(ind,1),'yyyy-mm-dd HH:MM:ss.FFF')
 figure,plot(diff(data.GYR(:,1))*24*60*60)
 ylim([0 0.02])
 figure,plot(diff(data.ACC(:,1))*24*60*60)
 ylim([0 0.02])