import numpy
import numpy as np
import matplotlib.pyplot as plt
import h5py
from utils import GenerateSyntheticNoise, DecodeEventBasedRawData

# variables
fileDirectory = 'C:\\Users\\Admin\\OneDrive\\Desktop\\UniBE\\data\\'
fileName = '150525_530_15_1a_DRC470_02.brw'
wellID = 'Well_A1'
useSyntheticNoise = True
dataStartPositionSec = 0
dataDurationSec = 3
# open the BRW file
file = h5py.File(fileDirectory + fileName, 'r')
# collect experiment information
samplingRate = file.attrs['SamplingRate']
chIdxs = np.array(file[wellID + '/StoredChIdxs'])
# convert the requested time interval from seconds to frames
startFrame = int(dataStartPositionSec * samplingRate)
numFrames = int(dataDurationSec * samplingRate)
# initialize an empty (fill with zeros) data collection
data = {}
for chIdx in chIdxs:
    data[chIdx] = np.zeros(numFrames, dtype=numpy.int16)

# fill the data collection with Gaussian noise if requested
if useSyntheticNoise:
    GenerateSyntheticNoise(file, data, wellID, startFrame, numFrames)
# fill the data collection with the decoded event based sparse raw data
DecodeEventBasedRawData(file, data, wellID, startFrame, numFrames)
# close the file
file.close()
# visualize the decoded raw signal from the first channel
x = np.arange(startFrame, startFrame + numFrames, 1) / samplingRate
y = np.fromiter(data[chIdxs[0]], float)
plt.figure()
plt.plot(x, y, color='blue')
plt.title('Raw Signal')
plt.xlabel('(sec)')
plt.ylabel('(ADC Count)')
plt.show()