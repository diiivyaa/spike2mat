import numpy as np
import h5py, time
from scipy.io import savemat

def DecodeEventBasedRawData(file, data, wellID):  
    # decode all data for the given well ID and time interval 
    binaryData = file[wellID + '/EventsBasedSparseRaw'][:] 
    binaryDataLength = len(binaryData)
 
    pos = 0 
    i = 0
    while pos < binaryDataLength: 
        chIdx = int.from_bytes(binaryData[pos:pos + 4], byteorder='little', signed=True) 
        if chIdx not in chIdxs:
            continue
        print(chIdx)
        pos += 4 
 
        chDataLength = int.from_bytes(binaryData[pos:pos + 4], byteorder='little', signed=True) 
        pos += 4 
 
        chDataPos = pos 
        while pos < chDataPos + chDataLength:  # loop till the end of the byte=pos+length of byte
            # Get start and end frames for this chunk of recorded date
            fromInclusive = int.from_bytes(binaryData[pos:pos + 8], byteorder='little', signed=True) # Start frame
            pos += 8 
 
            toExclusive = int.from_bytes(binaryData[pos:pos + 8], byteorder='little', signed=True)  # End frame 
            pos += 8 

            rangeDataPos = pos 
            lst = []
            # Loop within the actual spike event. Each iteration corresponds to one sample point recorded by device at frame j
            for _ in range(fromInclusive, toExclusive):  # Loop within the actual spike event
                lst.append(int.from_bytes(binaryData[rangeDataPos:rangeDataPos + 2], byteorder='little', signed=True)) # Each sample (spike amplitude) is 2 bytes.
                # print('data', int.from_bytes(binaryData[rangeDataPos:rangeDataPos + 2], byteorder='little', signed=True))
                rangeDataPos += 2 # Move to the next point (forward by 2 bytes)
            pos += (toExclusive - fromInclusive) * 2  # skip ahead by 2 bytes per frame
            data[chIdx].append(lst)

start = time.time()

# variables
filePath = 'C:\\Users\\Admin\\UniBE\\data\\220525_530_19_1b_DRC470_02\\220525_530_19_1b_DRC470_02.brw'
wellID = 'Well_A1'

# open the BRW file
file = h5py.File(filePath, 'r')

# collect experiment information
minDigitalValue = file.attrs['MinDigitalValue'] 
maxDigitalValue = file.attrs['MaxDigitalValue'] 
minAnalogValue = file.attrs['MinAnalogValue'] 
maxAnalogValue = file.attrs['MaxAnalogValue'] 
samplingRate = file.attrs['SamplingRate']
chIdxs = np.array(file[wellID + '/StoredChIdxs'])

# data
raw = np.array(file[wellID + '/EventsBasedSparseRaw'])
TOC = np.array(file[wellID + '/EventsBasedSparseRawTOC'])

# initialize an empty (fill with zeros) data collection 
data = {} 
for chIdx in chIdxs: 
    data[chIdx] = []

print("Start decoding brw file......")

DecodeEventBasedRawData(file, data, wellID)


print("Done decoding brw file......")
print("Convert to matlab compatible file......")

new = {}
for key in data.keys():
    str_key =  f'ch_{key}'
    if data[key]:
        new[str_key] = np.zeros(len(data[key]), dtype=object)
        for i in range(len(data[key])):
            new[str_key][i] = np.array(data[key][i], dtype=int)

print("Done conversion......")

savemat("brw_output.mat", new)

end = time.time()

print(f"Time taken to run: {end - start}")

print(new)