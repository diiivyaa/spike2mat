import h5py, os, cv2, pathlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.widgets import Cursor
from collections import Counter
from scipy.io import savemat
from sklearn.decomposition import PCA
from matplotlib.widgets import LassoSelector

class MEAPipeline():
    def __init__(self):
        pass
    
    def read_files(self,  bxr_path, img_path):
        '''Reads and checks if the bxr file is valid'''
        self.bxr_path= os.path.abspath(bxr_path.replace('"', ''))
        self.img_path = os.path.abspath(img_path.replace('"', ''))
        self.f_name = pathlib.Path(self.bxr_path).stem
        try:
            self.wellID = 'Well_A1' # identifier of chip well to be analysed 
            self.file = h5py.File(self.bxr_path, 'r')
        except FileNotFoundError:
            raise FileNotFoundError(f"The file '{self.bxr_path}' was not found.")
        except IOError:
            raise IOError(f"The file '{self.bxr_path}' could not be read (maybe corrupted or inaccessible).")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while reading '{self.file}': {e}")
        else:
            print("File read successfully!")
    
    def get_var(self):
        '''Gets the experiment data and information from the bxr file'''

        if not hasattr(self, 'file'):  # check to see if the pre-requistite method is called
            raise RuntimeError("File not loaded. Call read_file() before get_var().")

        # collect experiment information 
        self.minDigitalValue = self.file.attrs['MinDigitalValue'] 
        self.maxDigitalValue = self.file.attrs['MaxDigitalValue'] 
        self.minAnalogValue = self.file.attrs['MinAnalogValue'] 
        self.maxAnalogValue = self.file.attrs['MaxAnalogValue'] 
        self.dacFactor = (self.maxAnalogValue - self.minAnalogValue) / (self.maxDigitalValue - self.minDigitalValue) 
        self.offsetValue = self.minAnalogValue - self.dacFactor * self.minDigitalValue 
        self.samplingRate = self.file.attrs['SamplingRate']
        self.chIdxs = np.array(self.file[self.wellID + '/StoredChIdxs']) 

        # collect the required spike data 
        self.spikeDataTimestamps = self.file[self.wellID + '/SpikeTimes'][:] 
        self.spikeDataChIdxs = self.file[self.wellID + '/SpikeChIdxs'][:]
        print(np.any(self.spikeDataChIdxs == 1))
        self.spikeDataWaveforms = self.file[self.wellID + '/SpikeForms'][:] 
        self.waveformLength = self.file[self.wellID + '/SpikeForms'].attrs['Wavelength'] 

        return [self.minDigitalValue, self.maxDigitalValue, self.minAnalogValue, self.maxAnalogValue, self.waveformLength,  
                self.dacFactor, self.offsetValue, self.samplingRate, self.chIdxs, self.spikeDataWaveforms]
    
    def get_heatmap(self, savePath, dpi=17.5):  # set threshold as input
        '''Computes channel frequency and plots the activity map'''

        if not hasattr(self, 'spikeDataChIdxs'):  # check to see if the pre-requistite method is called
            raise RuntimeError("Variables not loaded. Call get_var() before get_heatmap().")

        counts = dict(Counter(self.spikeDataChIdxs))
        self.counts_array = np.zeros((64, 64))

        for key in counts.keys():
            r, c = key//64, key%64
            if counts[key] > 50000 or counts[key] < 30:
                self.counts_array[r][c] = 0
            elif r == 0 and c == 1:
                self.counts_array[r][c] = counts[key]
            else:
                self.counts_array[r][c] = counts[key]

        fig = plt.Figure(figsize=(64/dpi,64/dpi), dpi=dpi)
        plt.imshow(self.counts_array, cmap='hot', interpolation='none')
        plt.axis('off')
        self.heatmap_path = os.path.join(savePath, ''.join([self.f_name, '.png']))  # keep heatmap path for subsequent setps
        plt.savefig(self.heatmap_path, bbox_inches='tight', pad_inches=0, dpi=dpi)
        plt.axis('on')
        plt.colorbar()
        plt.show()
    
    def select_landmark(self):
        '''Interactive user landmark points selection'''

        if not hasattr(self, 'img_path'):  # check to see if the pre-requistite method is called
            raise RuntimeError("File not loaded. Call read_file() before select_landmark().")

        self.img = plt.imread(self.img_path)
        fig, ax = plt.subplots()
        ax.imshow(self.img)
        cursor = Cursor(ax, useblit=True, color='blue', linewidth=1)  # crosshair
        plt.title("Click 4 Points")

        self.points = plt.ginput(4, timeout=0)  # Click 4 points on the image

        # Unzip the list of (x, y) points
        x_vals, y_vals = zip(*self.points)
        plt.plot(x_vals, y_vals, 'bo')  # Blue circle markers

        plt.title("Selected Points")
        plt.draw()

        plt.show()
        print(self.points)
    
    def transform(self):
        '''Transforms the MEA image to align with the heatmap perspective'''
        
        if not hasattr(self, 'heatmap_path'):  # check to see if the pre-requistite method is called
            raise RuntimeError("Heatmap not generated. Call get_heatmap() before get_contours().")
        elif not hasattr(self, 'points') or  not hasattr(self, 'img'):
            raise RuntimeError("Landmark selection not done. Call select_landmark() before get_contours().")

        self.heatmap = cv2.imread(self.heatmap_path) 
        # plt.imread --> 4-channel images (R, G, B, alpha) so use cv2.imread instead for 3-channel images

        # Points on the heatmap
        dst_pts = np.array([
            [0, 0],      # top-left of heatmap
            [63, 0],     # top-right
            [63, 63],    # bottom-rigt
            [0, 63]      # bottom-left
        ], dtype=np.float32)

        # Corresponding points on the image
        src_pts = np.array(self.points, dtype=np.float32)

        # Transform
        self.matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

        # wrap heatmap to image shape
        height, width, _ = self.heatmap.shape
        wrapped_img = cv2.warpPerspective(self.img, self.matrix, (width, height))

        # Normalise and colour heatmap
        img_norm = cv2.normalize(wrapped_img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        img_colour = cv2.applyColorMap(img_norm, cv2.COLORMAP_JET)

        # Overlay
        alpha = 0.5
        self.overlay = cv2.addWeighted(self.heatmap, 1-alpha, cv2.cvtColor(img_colour, cv2.COLOR_RGB2BGR), alpha, 0)
    
    def draw_contours(self):
        '''Draw the sample's contour manually'''
        
        if not hasattr(self, 'matrix'):  # check to see if the pre-requistite method is called
            raise RuntimeError("Image not transformed. Call transform() before draw_contours().")

        # Region selection
        state = {
            'drawing': False,
            'mode': True,
            'contour': []
        }

        # Mouse callback function
        def draw(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                state['drawing'] = True
                state['current_x'], state['current_y'] = x, y
                state['contour'].append((x, y))

            elif event == cv2.EVENT_MOUSEMOVE and state['drawing']:
                if state['mode']:
                    cv2.line(state['image'], (state['current_x'], state['current_y']), (x, y), (255, 0, 0), 2)
                    state['current_x'], state['current_y'] = x, y
                    state['contour'].append((x, y))

            elif event == cv2.EVENT_LBUTTONUP:
                state['drawing'] = False
                if state['mode']:
                    cv2.line(state['image'], (state['current_x'], state['current_y']), (x, y), (0, 0, 255), 2)
                    state['contour'].append((x, y))
                    if len(state['contour']) > 2:
                        cv2.line(state['image'], (x, y), state['contour'][0], (0, 0, 255), 2)

        state['image'] = cv2.imread(self.img_path)
        window_name = "Draw Contours"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, draw)

        while True:
            cv2.imshow(window_name, state['image'])
            k = cv2.waitKey(1) & 0xFF
            if k == ord('m'):
                state['mode'] = not state['mode']
            elif k == 27:  # ESC
                break

        cv2.destroyAllWindows()

        contour_array = np.array(state['contour'], dtype=np.float32).reshape(-1, 1, 2)
        self.transformed_contour = cv2.perspectiveTransform(contour_array, self.matrix)
        cv2.drawContours(self.heatmap, [self.transformed_contour.astype(int)], 0, (0, 255, 0), thickness=cv2.FILLED)
        return self.transformed_contour
    
    def get_contours(self, threshold=25):
        '''Detects the sample's contour automatically'''
        
        if not hasattr(self, 'img'):
            raise RuntimeError("Landmark selection not done. Call select_landmark() before get_contours().")

        # Contour detection
        img_copy = self.img.copy()
        gray = cv2.cvtColor(img_copy, cv2.COLOR_BGR2GRAY)

        _, thresholded = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)

        cv2.imshow("Thresholded", thresholded)
        cv2.waitKey(0)  # Wait for any key press to close the window
        cv2.destroyAllWindows()
            
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
                best_contour = contour

        # Transform
        contour = best_contour.astype('float32') # Ensure type is float32
        self.transformed_contour = cv2.perspectiveTransform(contour, self.matrix)
        return self.transformed_contour

    def get_coords(self):
        '''Get 8-connected neighbours for the transformed'''
        
        if not hasattr(self, 'matrix'):  # check to see if the pre-requistite method is called
            raise RuntimeError("Image not transformed. Call transform() before draw_contours().")
    
        contour_copy = np.copy(self.transformed_contour)
        
        new_points, seen_neighbours = [], set()
        for i in range(len(self.transformed_contour)-1):
            x, y = self.transformed_contour[i][0]
            next_point = self.transformed_contour[i+1][0]
            for dx, dy in ([-1,-1], [-1,0], [-1,1], [0,1], [1,1], [1,0], [1,-1], [0,-1]): # 8-connected neighbor offsets in clockwise order starting from the top-left
                neighbour = (x + dx, y + dy)
                if not np.array_equal(next_point, neighbour) and neighbour not in seen_neighbours:
                    seen_neighbours.add(neighbour)
                    new_points.append([[neighbour[0], neighbour[1]]])  # keep consistent shape

        # Convert to correct shape and append
        if new_points:
            contour_copy = np.vstack([contour_copy, new_points])

        contour_copy = np.array(sorted(contour_copy, key=lambda x: x[0][0]), dtype=object)

        cv2.drawContours(self.overlay, [contour_copy.astype(int)], -1, (0, 255, 0), 2)
        cv2.drawContours(self.overlay, [self.transformed_contour.astype(int)], 0, (255, 0, 0), 2)
        cv2.drawContours(self.heatmap, [contour_copy.astype(int)], 0, (0, 255, 0), thickness=cv2.FILLED)
        cv2.imshow("Contours", self.overlay)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        return contour_copy
    
    def get_channels(self):
        '''Identifies active electrode channels based on the contour overlay.'''

        if not hasattr(self, 'heatmap'):  # check to see if the pre-requistite method is called
            raise RuntimeError("Contours not detected. Call get_contours() before get_channels().")
        elif not hasattr(self, 'counts_array'):
            raise RuntimeError("Heatmap not generated. Call get_heatmap() before get_channels().")
        
        mask = np.all(self.heatmap == [0, 255, 0], axis=-1)  # take extra channels
        coords = np.column_stack(np.where(mask))
        cleaned_heatmap = np.zeros((64, 64))
        self.channels = []
        for point in coords:
            x, y = point
            cleaned_heatmap[x][y] = self.counts_array[x][y]
            self.channels.append(64*x+y)
            # coordinate conventions differ between image and heatmaps (i.e., x and y are flipped)
        cleaned_heatmap[0][1] = self.counts_array[0][1]
        self.channels.append(64*0+1)

        fig = plt.Figure()
        plt.imshow(cleaned_heatmap, cmap='hot', interpolation='bilinear')
        plt.axis('on')
        plt.colorbar()
        plt.show()
    
    def align_time(self):
        '''Align time data based on channel (1,2) which is (0,1) in the array notation'''
        
        if any(not hasattr(self, attr) for attr in ['spikeDataChIdxs', 'spikeDataTimestamps']):  # check to see if the pre-requistite method is called
            raise RuntimeError("Variables not loaded. Call get_var() before to_mat().")
        
        self.offset = 0
        for idx, ch in enumerate(self.spikeDataChIdxs): 
            if ch == 1:
                # print(self.spikeDataTimestamps[idx]/self.samplingRate)    # Get the first timestamp in channel 1 (1, 2)
                self.offset = int(self.spikeDataTimestamps[idx]/self.samplingRate - 30)
                break  # to stop from looping
        print(self.offset)
    
    def to_mat(self, savePath):
        '''Convert and format data to a MAT file'''

        if any(not hasattr(self, attr) for attr in ['spikeDataChIdxs', 'spikeDataTimestamps', 'offsetValue', \
                                                    'spikeDataWaveforms', 'waveformLength', 'dacFactor']):  # check to see if the pre-requistite method is called
            raise RuntimeError("Variables not loaded. Call get_var() before to_mat().")
        elif not hasattr(self, 'offset'):
            raise RuntimeError("Offset not computed. Call align_time() before to_mat().")
        
        waveformData, timeData = {}, {}
        for idx, ch in enumerate(self.spikeDataChIdxs):
            if ch in self.channels:
                if ch not in waveformData:
                    waveformData[ch] = []
                    timeData[ch] = []
                
                time_s = (self.spikeDataTimestamps[idx]/self.samplingRate) - self.offset  # in seconds
                waveform = self.spikeDataWaveforms[idx * self.waveformLength : (idx + 1) * self.waveformLength]
                spikemV = [self.offsetValue + i * self.dacFactor for i in waveform] # convert digital signal to microvolt
                
                if 0 <= time_s <= 750:
                    waveformData[ch].append(spikemV)  # store both!
                    timeData[ch].append(time_s)
        
        # remove empty lists
        waveformData = {k:v for k,v in waveformData.items() if v}
        timeData = {k:v for k,v in timeData.items() if v}

        keys, copy = list(waveformData.keys()), list(waveformData.keys())
        spikeArray, timeArray = [], []
        for i in range(len(keys)):  
            if 30 <= len(waveformData[keys[i]]) <= 100000:
                spikeArray.append(np.asarray(waveformData[keys[i]], dtype=np.float64))
                arr = np.asarray(timeData[keys[i]], dtype=np.float64)
                timeArray.append(arr.reshape(-1, 1))
            else:
                copy.remove(keys[i])

        # Format list to numpy column vector
        spikeArray = np.array(spikeArray, dtype=object).reshape(-1, 1)
        timeArray = np.array(timeArray, dtype=object).reshape(-1, 1)
        channels_arr = np.array(copy, dtype=np.float64).reshape(-1, 1)

        # Convert to MATLAB-compatible format
        mat_data = {
            'spikearray_uV': spikeArray,
            'spikeTimearray': timeArray,
            'channels': channels_arr,
            'spikemaxmV': float(self.maxAnalogValue),
            'spikeminmV': float(self.minAnalogValue)
        }

        # Save to .mat file
        savemat(os.path.join(savePath, ''.join([self.f_name, '.mat'])), mat_data)
    
    def get_waveform(self, chIdx=2899, start=0, end=500):
        '''Selects and plots waveforms for a specified channel within a given time range.'''
        # Start and end of recording interval
        dataStartPosition = start
        dataDurationSec = end
        self.chIdx = chIdx

        # convert the requested time interval from seconds to frames 
        startFrame = int(dataStartPosition * self.samplingRate) 
        nFrames = int(dataDurationSec * self.samplingRate) 
        print('frames', startFrame, nFrames)

        # collect the TOCs 
        toc = np.array(self.file['TOC']) 
        spikeToc = np.array(self.file[self.wellID + '/SpikeTOC']) 
        
        # from the given start position and duration (in frames), find the corresponding range of spike positions using the TOC 
        tocStartIdx = np.searchsorted(toc[:, 1], startFrame) 
        tocEndIdx = min(np.searchsorted(toc[:, 1], startFrame + nFrames, side='right') + 1, len(toc) - 1) 
        spikeStart = spikeToc[tocStartIdx]
        spikeEnd = spikeToc[tocEndIdx]
        selected_spikeDataWaveforms = self.spikeDataWaveforms[spikeStart*self.waveformLength:spikeEnd*self.waveformLength] 

        self.waveformData = [] 
        for idx, ch in enumerate(self.spikeDataChIdxs): 
            if ch == chIdx and startFrame <= self.spikeDataTimestamps[idx] < startFrame + nFrames:
                self.waveformData.append(selected_spikeDataWaveforms[idx*self.waveformLength:idx*self.waveformLength+self.waveformLength])
        
        self.x = np.arange(0, self.waveformLength, 1) / self.samplingRate 
        for i in range(len(self.waveformData)):
            # convert the waveform to analog 
            y = self.offsetValue + self.dacFactor * self.waveformData[i]
            plt.plot(self.x, y, color='blue', alpha=0.3)
        
        return self.waveformData

    def pca(self, n=3):
        pca = PCA(n_components=n)
        self.pca_scaled = pca.fit_transform(self.waveformData)
        return self.pca_scaled
    
    def select_waveform(self):
       def on_select(verts):
            path = Path(verts)
            
            global mask
            mask = path.contains_points(self.pca_scaled[:, [0,1]])
            print(dict(Counter(mask)))

            fig = plt.figure()
            for i in range(len(self.waveformData)):
                y = self.offsetValue + self.dacFactor * self.waveformData[i]
                if mask[i]:  # if waveform is selected
                    plt.plot(self.x, y, color='yellow')  # highlight selected in red
                else:
                    plt.plot(self.x, y, color='blue', alpha=0.3)
            plt.show()

            fig, ax = plt.subplots()
            ax.scatter(self.pca_scaled[:, 0], self.pca_scaled[:, 1], s=1)
            plt.xlabel('PC 1')
            plt.ylabel('PC 2')
            plt.title(f'PCA of Spike Waveforms - Channel {self.chIdx}')

            selector = LassoSelector(
                ax, on_select,
                useblit=True,       
                button=[1, 3],
                props=dict(color='yellow', linewidth=2, linestyle='-') 
            )
            plt.show()
    
    def run(self, savePath, bxr_path, img_path, threshold=25):
        self.read_files(bxr_path, img_path)
        self.get_var()
        self.get_heatmap(savePath)
        self.select_landmark()
        self.transform()
        self.get_contours(threshold)
        self.get_coords()
        # self.draw_contours()
        self.get_channels()
        self.align_time()
        self.to_mat(savePath)

if __name__ == '__main__':
    # read input from the user
    img_path = input('Image path: ')
    bxr_path = input('BXR file path: ')
    
    si = MEAPipeline()
    si.run(savePath=r"C:\Users\Admin\UniBE\data\200525", bxr_path=bxr_path, img_path=img_path, threshold=35)
