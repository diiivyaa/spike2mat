import h5py, os
import numpy as np
import matplotlib.pyplot as plt

# define variables 
fileDirectory = 'C:\\Users\\Admin\\UniBE\\data\\220525_530_19_1b_DRC470_02\\'
fileName = '220525_530_19_1b_DRC470_02_2.bxr'
wellID = 'Well_A1' # identifier of chip well to be analysed 
dataStartPositionSec = 0 # start position in seconds of the portion to extract and plot 
dataDurationSec = 797.07 # duration in seconds of the portion to extract and plot 

# open the BXR file 
file = h5py.File(fileDirectory + fileName, 'r')
chIdxs = np.array(file[wellID + '/StoredChIdxs']) 

# for i in range(len(chIdxs)-4000):
chIdx = 92

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
dataLength = spikeEndPosition - spikeStartPosition 

waveformLength = file[wellID + '/SpikeForms'].attrs['Wavelength'] 
spikeDataWaveforms = file[wellID + '/SpikeForms'][spikeStartPosition*waveformLength:spikeEndPosition*waveformLength] 

waveformData = [] 
for i in range(0, dataLength): 
    if spikeDataChIdxs[i] == chIdx and startFrame <= spikeDataTimestamps[i] < startFrame + nFrames: 
        waveformData.append(spikeDataWaveforms[i*waveformLength:i*waveformLength+waveformLength]) 

x = np.arange(0, waveformLength, 1) / samplingRate 
for waveform in waveformData: 
# waveform = waveformData[3]
    # convert the waveform to analog 
    y = offsetValue + dacFactor * waveform 
    plt.plot(x, y, color='blue', alpha=0.3)
# save_path = os.path.join('C:\\Users\\Admin\\UniBE\\plots', f'{chIdx}.png')
# plt.savefig(save_path)
plt.show()
plt.close()