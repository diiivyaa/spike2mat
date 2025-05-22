import h5py, os
import numpy as np
from scipy.io import savemat

# Step 1: Read spike times from .bxr file
fileDirectory = 'C:\\Users\\Admin\\UniBE\\data\\'
fileName = '150525_530_15_1a_DRC470_02.bxr'
wellID = 'Well_A1'

# open the BXR file 
file = h5py.File(os.path.join(fileDirectory,fileName), 'r')

# metadata
minDigitalValue = file.attrs['MinDigitalValue'] 
maxDigitalValue = file.attrs['MaxDigitalValue'] 
minAnalogValue = file.attrs['MinAnalogValue'] 
maxAnalogValue = file.attrs['MaxAnalogValue'] 
dacFactor = (maxAnalogValue - minAnalogValue) / (maxDigitalValue - minDigitalValue) 
offsetValue = minAnalogValue - dacFactor * minDigitalValue 
samplingRate = file.attrs['SamplingRate'] 

# collect the required spike data 
spikeDataTimestamps = file[wellID + '/SpikeTimes'][:] 
spikeDataChIdxs = file[wellID + '/SpikeChIdxs'][:]
spikeForms = file[wellID + '/SpikeForms']
spikeTOC = file[wellID + '/SpikeTOC']

waveformLength = file[wellID + '/SpikeForms'].attrs['Wavelength'] 
spikeDataWaveforms = file[wellID + '/SpikeForms'][:] 

waveformData, timeData = {}, {}
for idx, ch in enumerate(spikeDataChIdxs):
    if ch not in waveformData:
        waveformData[ch] = []
        timeData[ch] = []
    
    time_s = spikeDataTimestamps[idx]/samplingRate  # in seconds
    waveform = spikeDataWaveforms[idx * waveformLength : (idx + 1) * waveformLength]
    spikemV = [offsetValue + i * dacFactor for i in waveform] # convert digital signal to microvolt
    
    waveformData[ch].append(spikemV)  # store both!
    timeData[ch].append(time_s)

arraySize = 64
spikeArray, timeArray = np.empty((arraySize, arraySize), dtype=object), np.empty((arraySize, arraySize), dtype=object)
for i in range(arraySize**2):
    r, c = i//64, i%64  
    if i in waveformData.keys():
        spikeArray[r][c] = np.array(waveformData[i])
    else: 
        spikeArray[r][c] = np.zeros((1, waveformLength), dtype=np.int16)

    if i in timeData.keys():
        timeArray[r][c] = np.array(timeData[i])
    else: 
        timeArray[r][c] = np.zeros((waveformLength, 1), dtype=np.int16)

# Convert to MATLAB-compatible format
mat_data = {
    'spikearray_uV': spikeArray,
    'spikeTimearray': timeArray,
    'spikemaxmV': float(maxAnalogValue),
    'spikeminmV': float(minAnalogValue)
}

# Save to .mat file
savemat(os.path.join('C:\\Users\\Admin\\UniBE\\data', 'waveform_data.mat'), mat_data)
