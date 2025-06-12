import h5py, os, cv2
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
from itertools import combinations

# define variables 
fileDirectory = 'C:\\Users\\Admin\\UniBE\\data\\200525' # 150525_530_15_1a_DRC470_02
fileName = '200525_531_18_1a_DRC470_03_thre6.bxr' # '150525_530_15_1a_DRC470_02.bxr'
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

    for i in range(10):
        img = plt.imread("C:\\Users\\Admin\\UniBE\\data\\200525\\thumbnail_IMG_3331.jpg")
        plt.imshow(img)
        points = plt.ginput(4)  # Click 4 points on the image   
        print(points)
        plt.close()

        heatmap = cv2.imread("C:\\Users\\Admin\\UniBE\\data\\200525\\heatmap.png") 
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

        _, thresholded = cv2.threshold(gray, 35, 255, cv2.THRESH_BINARY_INV)
            
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

        contour_copy = np.copy(transformed_contour)

        new_points, seen_neighbours = [], set()
        for i in range(len(transformed_contour)-1):
            x, y = transformed_contour[i][0]
            next_point = transformed_contour[i+1][0]
            for dx, dy in ([-1,-1], [-1,0], [-1,1], [0,1], [1,1], [1,0], [1,-1], [0,-1]): # 8-connected neighbor offsets in clockwise order starting from the top-left
                neighbour = (x + dx, y + dy)
                if not np.array_equal(next_point, neighbour) and neighbour not in seen_neighbours:
                    seen_neighbours.add(neighbour)
                    new_points.append([[neighbour[0], neighbour[1]]])  # keep consistent shape

        # Convert to correct shape and append
        if new_points:
            # new_points_array = np.array(new_points, dtype=copy.dtype)
            contour_copy = np.vstack([contour_copy, new_points])
        contour_copy = np.array(sorted(contour_copy, key=lambda x: x[0][0]), dtype=object)

        cv2.drawContours(heatmap, [contour_copy.astype(int)], 0, (0, 255, 0), thickness=cv2.FILLED)

        mask = np.all(heatmap == [0, 255, 0], axis=-1)  # take extra channels
        coords = np.column_stack(np.where(mask))
        cleaned_heatmap = np.zeros((64, 64))
        channels = []
        for point in coords:
            x, y = point
            cleaned_heatmap[x][y] = counts_array[x][y]
            channels.append(64*x+y)
            # coordinate conventions differ between image and heatmaps (i.e., x and y are flipped)

        channel_sets.append(set(channels))
        src_pts, dst_pts, channels = 0, 0, 0

    # Compute Jaccard similarity between all file pairs
    jaccard_similarities = []
    for set1, set2 in combinations(channel_sets, 2):
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        jaccard = intersection / union if union > 0 else 0
        jaccard_similarities.append(jaccard)

    # Calculate average similarity and % variation
    average_jaccard = sum(jaccard_similarities) / len(jaccard_similarities)
    percent_variation = 100 * (1 - average_jaccard)

    print(f"Average Jaccard Similarity: {average_jaccard:.2f}")
    print(f"Percentage Variation in Channel Selection Across Files: {percent_variation:.2f}%")

    # heatmap/histogram on how many times the channels appears every run
    counts = {}
    counts_array = np.zeros((64, 64))

    for channel in channel_sets:
        counts_dict = dict(Counter(channel))
        for key in counts_dict.keys():
            if key in counts.keys():
                counts[key] = counts[key] + counts_dict[key]
            else:
                counts[key] = counts_dict[key]
    for key in counts.keys():
        r, c = key//64, key%64
        if counts[key] > 40000:
            counts_array[r][c] = 0
        else:
            counts_array[r][c] = counts[key]

    fig = plt.Figure()
    plt.imshow(counts_array, cmap='hot', interpolation='none')
    plt.colorbar()
    plt.show()

if __name__ == "__main__":
    main()
