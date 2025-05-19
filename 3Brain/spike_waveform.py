import numpy as np 
import matplotlib.pyplot as plt 
import matplotlib.colors as mcolors 
import h5py 
 
# define variables 
fileDirectory = 'C:\\Users\\Admin\\OneDrive\\Desktop\\UniBE\\data\\'
fileName = '150525_530_15_1a_DRC470_02.bxr'
chIdx = 280 # identifier of channel to be analysed 
wellID = 'Well_A1' # identifier of chip well to be analysed 
 
dataStartPositionSec = 2 # start position in seconds of the portion to extract and plot 
dataDurationSec = 5 # duration in seconds of the portion to extract and plot 
 
# open the BXR file 
file = h5py.File(fileDirectory + fileName, 'r') 
 
# collect experiment information 
minDigitalValue = file.attrs['MinDigitalValue'] 
maxDigitalValue = file.attrs['MaxDigitalValue'] 
minAnalogValue = file.attrs['MinAnalogValue'] 
maxAnalogValue = file.attrs['MaxAnalogValue'] 
dacFactor = (maxAnalogValue - minAnalogValue) / (maxDigitalValue - minDigitalValue) 
offsetValue = minAnalogValue - dacFactor * minDigitalValue 
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
 
spikeSortingPerformed = file.__contains__(wellID + '/SpikeUnits') 
if spikeSortingPerformed: 
    spikeDataChUnits = file[wellID + '/SpikeUnits'][spikeStartPosition:spikeEndPosition] 
 
waveformLength = file[wellID + '/SpikeForms'].attrs['Wavelength'] 
spikeDataWaveforms = file[wellID + 
'/SpikeForms'][spikeStartPosition*waveformLength:spikeEndPosition*waveformLength] 
dataLength = spikeEndPosition - spikeStartPosition 
 
# collect the waveforms for the given time range and channel index 
waveformData = {} if spikeSortingPerformed else [] 
for i in range(0, dataLength): 
    if spikeDataChIdxs[i] == chIdx and startFrame <= spikeDataTimestamps[i] < startFrame + nFrames: 
        if spikeSortingPerformed: 
            spikeUnit = spikeDataChUnits[i] 
            if spikeUnit not in waveformData.keys(): 
                waveformData[spikeUnit] = [] 
            waveformData[spikeUnit].append(spikeDataWaveforms[i*waveformLength:i*waveformLength 
                                                                                    +waveformLength]) 
        else: 
            waveformData.append(spikeDataWaveforms[i*waveformLength:i*waveformLength+waveformLength]) 
 
# close the BXR file 
file.close() 
 
# visualize waveforms for the given channel index, if spike sorting was performed, 
# units will be plotted with different colors 
plt.figure() 
x = np.arange(0, waveformLength, 1) / samplingRate 
 
if spikeSortingPerformed: 
    colors = list(mcolors.BASE_COLORS.keys()) 
    c = 0 
    for unit in waveformData: 
        for waveform in waveformData[unit]: 
            # convert the waveform to analog 
            y = offsetValue + dacFactor * waveform 
            plt.plot(x, y, color=colors[c]) 
        c += 1 
else: 
    for waveform in waveformData: 
        # convert the waveform to analog 
        y = offsetValue + dacFactor * waveform 
        plt.plot(x, y, color='blue') 
 
plt.title('Spike waveforms') 
plt.xlabel('(sec)') 
plt.ylabel('(uV)') 
plt.legend() 
plt.show() 
