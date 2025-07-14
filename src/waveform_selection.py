import h5py, os, cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
from collections import Counter

# define variables 
fileDirectory = 'C:\\Users\\Admin\\UniBE\\data\\220525_530_19_1b_DRC470_02' # 150525_530_15_1a_DRC470_02
fileName = '220525_530_19_1b_DRC470_02_2.bxr' # '150525_530_15_1a_DRC470_02.bxr'
wellID = 'Well_A1' # identifier of chip well to be analysed 

def main():
    # open the BXR file 
    file = h5py.File(os.path.join(fileDirectory,fileName), 'r')

    # collect experiment information 
    minDigitalValue = file.attrs['MinDigitalValue'] 
    maxDigitalValue = file.attrs['MaxDigitalValue'] 
    minAnalogValue = file.attrs['MinAnalogValue'] 
    maxAnalogValue = file.attrs['MaxAnalogValue'] 
    dacFactor = (maxAnalogValue - minAnalogValue) / (maxDigitalValue - minDigitalValue) 
    offsetValue = minAnalogValue - dacFactor * minDigitalValue 
    samplingRate = file.attrs['SamplingRate']
    chIdxs = np.array(file[wellID + '/StoredChIdxs']) 

    # collect the required spike data 
    spikeDataTimestamps = file[wellID + '/SpikeTimes'][:] 
    spikeDataChIdxs = file[wellID + '/SpikeChIdxs'][:]

    counts = dict(Counter(spikeDataChIdxs))
    counts_array = np.zeros((64, 64))

    channel_sets = []

    for key in counts.keys():
        r, c = key//64, key%64
        if counts[key] > 40000:
            counts_array[r][c] = 0
        else:
            counts_array[r][c] = counts[key]

    dpi = 17.5

    fig = plt.Figure(figsize=(64/dpi,64/dpi), dpi=dpi)
    plt.imshow(counts_array, cmap='hot', interpolation='none')
    plt.axis('off')
    plt.savefig(os.path.join(fileDirectory, "heatmap.png"), bbox_inches='tight', pad_inches=0, dpi=dpi)

    plt.axis('on')
    plt.colorbar()
    plt.show()

    img = plt.imread("C:\\Users\\Admin\\UniBE\\data\\220525_530_19_1b_DRC470_02\\images\\image3.jpeg")
    plt.imshow(img)
    points = plt.ginput(4)  # Click 4 points on the image   
    print(points)
    plt.close()

    heatmap = cv2.imread("C:\\Users\\Admin\\UniBE\\data\\220525_530_19_1b_DRC470_02\\heatmap.png") 
    # plt.imread --> 4-channel images (R, G, B, alpha) so use cv2.imread instead for 3-channel images

    # Points on the heatmap
    dst_pts = np.array([
        [0, 0],      # top-left of heatmap
        [63, 0],     # top-right
        [63, 63],    # bottom-rigt
        [0, 63]      # bottom-left
    ], dtype=np.float32)

    # Corresponding points on the image
    src_pts = np.array(points, dtype=np.float32)

    # Transform
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

    # wrap heatmap to image shape
    height, width, _ = heatmap.shape
    wrapped_img = cv2.warpPerspective(img, matrix, (width, height))

    # Normalise and colour heatmap
    img_norm = cv2.normalize(wrapped_img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    img_colour = cv2.applyColorMap(img_norm, cv2.COLORMAP_JET)

    # Overlay
    alpha = 0.5
    overlay = cv2.addWeighted(heatmap, 1-alpha, cv2.cvtColor(img_colour, cv2.COLOR_RGB2BGR), alpha, 0)

    # Contour detection
    img_copy = img.copy()
    gray = cv2.cvtColor(img_copy, cv2.COLOR_BGR2GRAY)

    _, thresholded = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY_INV)
        
    # rectangular kernel (5x5)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))    # General kernel size
    cleaned = cv2.morphologyEx(thresholded, cv2.MORPH_OPEN, kernel)  # Remove noise
    closed = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)      # Fill gaps

    # Find contours
    inverted = cv2.bitwise_not(thresholded)
    contours, _ = cv2.findContours(inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    for contour in contours:
        area = cv2.contourArea(contour)  
        if area > 10000:
            print(area)
            best_contour = contour

    # Transform
    contour = best_contour.astype('float32') # Ensure type is float32
    transformed_contour = cv2.perspectiveTransform(contour, matrix)

    cv2.drawContours(overlay, [transformed_contour.astype(int)], 0, (0, 255, 0), 2)
    cv2.drawContours(heatmap, [transformed_contour.astype(int)], 0, (0, 255, 0), thickness=cv2.FILLED)

    mask = np.all(heatmap == [0, 255, 0], axis=-1)  # take extra channels
    coords = np.column_stack(np.where(mask))
    cleaned_heatmap = np.zeros((64, 64))
    channels = []
    for point in coords:
        x, y = point
        cleaned_heatmap[x][y] = counts_array[x][y]
        channels.append(64*x+y)
        # coordinate conventions differ between image and heatmaps (i.e., x and y are flipped)

    fig = plt.Figure()
    plt.imshow(cleaned_heatmap, cmap='hot', interpolation='bilinear')
    plt.axis('on')
    plt.colorbar()
    plt.show()

    mask = np.isin(spikeDataChIdxs, channels)
    spikeDataChIdxs[np.where(~mask)] = 0

    # Strta and end of recording interval
    dataStartPositionSec = 0
    dataDurationSec = 797.07

    # convert the requested time interval from seconds to frames 
    startFrame = int(dataStartPositionSec * samplingRate) 
    nFrames = int(dataDurationSec * samplingRate) 

    # collect the TOCs 
    toc = np.array(file['TOC']) 
    spikeToc = np.array(file[wellID + '/SpikeTOC']) 
    
    # from the given start position and duration (in frames), find the corresponding range of spike positions using the TOC 
    tocStartIdx = np.searchsorted(toc[:, 1], startFrame) 
    tocEndIdx = min(np.searchsorted(toc[:, 1], startFrame + nFrames, side='right') + 1, len(toc) - 1) 
    spikeStart = spikeToc[tocStartIdx]
    spikeEnd = spikeToc[tocEndIdx]

    waveformLength = file[wellID + '/SpikeForms'].attrs['Wavelength'] 
    spikeDataWaveforms = file[wellID + '/SpikeForms'][spikeStart*waveformLength:spikeEnd*waveformLength] 

    waveformData = [] 
    chIdx = 2899
    for idx, ch in enumerate(spikeDataChIdxs): 
        if ch == chIdx and startFrame <= spikeDataTimestamps[idx] < startFrame + nFrames:
            waveformData.append(spikeDataWaveforms[idx*waveformLength:idx*waveformLength+waveformLength])

    x = np.arange(0, waveformLength, 1) / samplingRate 

    from sklearn.decomposition import PCA
    pca = PCA(n_components=3)
    pcs = pca.fit_transform(waveformData)

    from matplotlib.widgets import LassoSelector

    def on_select(verts):
        path = Path(verts)
        
        global mask
        mask = path.contains_points(pcs[:, [0,1]])
        print(dict(Counter(mask)))

        fig = plt.figure()
        for i in range(len(waveformData)):
            y = offsetValue + dacFactor * waveformData[i]
            if mask[i]:  # if waveform is selected
                plt.plot(x, y, color='yellow', alpha=0.8)  # highlight selected in red
            else:
                plt.plot(x, y, color='blue', alpha=0.3)
        plt.show()


    fig, ax = plt.subplots()
    ax.scatter(pcs[:, 0], pcs[:, 1], s=1)
    plt.xlabel('PC 1')
    plt.ylabel('PC 2')
    plt.title(f'PCA of Spike Waveforms - Channel {chIdx}')

    selector = LassoSelector(
        ax, on_select,
        useblit=True,       
        button=[1, 3],
        props=dict(color='yellow', linewidth=2, linestyle='-') 
    )
    plt.show()

if __name__ == "__main__":
    main()
