import numpy as np 
import matplotlib.pyplot as plt 
import h5py 
# define variables 
fileDirectory = 'C:\\Users\\Admin\\OneDrive\\Desktop\\UniBE\\data\\'
fileName = '150525_530_15_1a_DRC470_02.bxr'
wellID = 'Well_A1' # identifier of chip well to be analysed 
dataStartPositionSec = 2 # start position in seconds of the portion to extract and plot 
dataDurationSec = 5 # duration in seconds of the portion to extract and plot 
# open the BXR file 
file = h5py.File(fileDirectory + fileName, 'r')

# collect experiment information 
samplingRate = file.attrs['SamplingRate'] 
chIdxs = np.array(file[wellID + '/StoredChIdxs']) 
 
# convert the requested time interval from seconds to frames 
startFrame = int(dataStartPositionSec * samplingRate) 
nFrames = int(dataDurationSec * samplingRate) 
 
# collect the TOCs 
toc = np.array(file['TOC']) 
spikeToc = np.array(file[wellID + '/SpikeTOC']) 
 
# from the given start position and duration (in frames), find the corresponding range of spike positions using the TOC 
tocStartIdx = np.searchsorted(toc[:, 1], startFrame) 
tocEndIdx = min(np.searchsorted(toc[:, 1], startFrame + nFrames, side='right') + 1, len(toc) - 1) 
spikeStartPosition = spikeToc[tocStartIdx] 
spikeEndPosition = spikeToc[tocEndIdx] 
 
# collect the required spike data 
spikeDataTimestamps = file[wellID + '/SpikeTimes'][spikeStartPosition:spikeEndPosition] 
spikeDataChIdxs = file[wellID + '/SpikeChIdxs'][spikeStartPosition:spikeEndPosition] 
dataLength = spikeEndPosition - spikeStartPosition 
 
# build the raster dataset with spike times and convert spike times from frame position to seconds for each channel 
rasterData = [[] for _ in chIdxs] 
for timestamp, ch_idx in zip(spikeDataTimestamps, spikeDataChIdxs): 
    if startFrame <= timestamp < startFrame + nFrames: 
        rasterData[ch_idx].append(timestamp / samplingRate) 
 
# close the BXR file 
file.close() 
 
# visualize the spike raster plot 
plt.figure() 
plt.eventplot(rasterData, colors='black') 
plt.title('Spikes Raster Plot') 
plt.xlabel('(sec)') 
plt.ylabel('(channel indexes)') 
plt.show()