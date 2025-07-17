import h5py, os, cv2, pathlib, itertools
import numpy as np
import numpy.ma as ma
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
from collections import Counter
from scipy.io import savemat
from matplotlib.colors import LogNorm
from PIL import Image, ExifTags

# Optional
from pipelineAnalysis import profile_algorithm

class MEAPipeline():
    def __init__(self):
        self.channels = []

    def read_files(self,  bxr_path, img_path):
        '''Reads and checks if the bxr file is valid'''
        self.bxr_path= os.path.abspath(bxr_path.replace('"', ''))
        self.img_path = os.path.abspath(img_path.replace('"', ''))
        if img_path:
            self.img_path = os.path.abspath(img_path.replace('"', ''))
        else:
            self.img_path = None
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
        self.spikeDataWaveforms = self.file[self.wellID + '/SpikeForms'][:] 
        self.waveformLength = self.file[self.wellID + '/SpikeForms'].attrs['Wavelength'] 

        self.align_flag = np.any(self.spikeDataChIdxs == 1)
    
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

        # Mask and handle low values
        mask = self.counts_array == 0
        counts_masked = ma.masked_array(self.counts_array, mask=mask)
        counts_masked[counts_masked < 1] = 1

        vmin = self.counts_array.min()
        vmax = self.counts_array.max()

        # Set output image size to exactly 64x64 pixels
        dpi = 83.5
        fig = plt.figure(figsize=(1, 1), dpi=dpi)

        # Plot heatmap
        ax = sns.heatmap(counts_masked, cmap='viridis', norm=LogNorm(vmin=vmin, vmax=vmax), cbar=False, ax=fig.add_subplot(111))
        ax.axis('off')

        # Save the figure
        self.heatmap_path = os.path.join(savePath, ''.join([self.f_name, '.png']))  # keep heatmap path for subsequent setps
        plt.savefig(self.heatmap_path, bbox_inches='tight', pad_inches=0, dpi=dpi)
        plt.close()
    
    def select_landmark(self):
        '''Interactive user landmark points selection'''

        if not hasattr(self, 'img_path'):  # check to see if the pre-requistite method is called
            raise RuntimeError("File not loaded. Call read_file() before select_landmark().")
        
        # Open image with PIL and correct orientation
        self.img_raw = Image.open(self.img_path)
        width, height = self.img_raw.size

        if width > 1500 or height > 1500:
            self.img_raw.thumbnail((1000, 1000), Image.Resampling.LANCZOS)

        # Handle EXIF orientation
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break

            exif = self.img_raw._getexif()
            if exif is not None:
                orientation_value = exif.get(orientation, None)

                if orientation_value == 3:
                    self.img_raw = self.img_raw.rotate(180, expand=True)
                elif orientation_value == 6:
                    self.img_raw = self.img_raw.rotate(270, expand=True)
                elif orientation_value == 8:
                    self.img_raw = self.img_raw.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            # If image has no EXIF data or cannot read orientation
            raise RuntimeError("Image file is corrupted. Please try again with another image.")

        # Convert to NumPy array and show
        self.img = plt.imread(self.img_path) if isinstance(self.img_raw, str) else np.array(self.img_raw)
        fig, ax = plt.subplots()
        ax.imshow(self.img)
        cursor = Cursor(ax, useblit=True, color='blue', linewidth=1)  # crosshair
        plt.title("Click 4 Points in clockwise direction")

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
        self.overlay = cv2.addWeighted(img_colour, 1-alpha, cv2.cvtColor(self.heatmap, cv2.COLOR_RGB2BGR), alpha, 0)

        # Resize for display
        matrix = cv2.getPerspectiveTransform(dst_pts, src_pts)
        height, width, _ = self.img.shape
        wrapped_heatmap = cv2.warpPerspective(self.heatmap, matrix, (width, height))
        self.resized = cv2.addWeighted(self.img, 1-alpha, wrapped_heatmap, 0.5, 0)
    
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

        self.img_bgr = cv2.cvtColor(np.array(self.img), cv2.COLOR_RGB2BGR)
        state['image'] = self.img_bgr
        window_name = "Draw Contours"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, draw)
        
        original_image = self.img_bgr.copy()  # Store a clean copy for reset

        while True:
            cv2.putText(state['image'], "Press 'r' to reset, 'm' to toggle mode, Enter to finish", 
            (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)
            cv2.imshow(window_name, state['image'])
            k = cv2.waitKey(1) & 0xFF
            if k == ord('m'):
                state['mode'] = not state['mode']
            elif k == ord('r'):  # Press 'r' to reset drawing
                state['image'] = original_image.copy()
                state['contour'].clear()
                state['drawing'] = False
                state['current_x'], state['current_y'] = 0, 0
            elif k == 13:  # Enter to exit
                break
        
        cv2.destroyAllWindows()

        contour_array = np.array(state['contour'], dtype=np.float32).reshape(-1, 1, 2)
        self.transformed_contour = cv2.perspectiveTransform(contour_array, self.matrix)
        cv2.drawContours(self.heatmap, [self.transformed_contour.astype(int)], 0, (0, 255, 0), thickness=cv2.FILLED)

        # For display
        cv2.drawContours(self.resized, [contour_array.astype(int)], -1, (0, 255, 0), 2)
        cv2.imshow("Contours", self.resized)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

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

        # For display
        cv2.drawContours(self.resized, [contour.astype(int)], -1, (0, 255, 0), 2)
        cv2.imshow("Contours", self.resized)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

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
        cv2.drawContours(self.heatmap, [contour_copy.astype(int)], 0, (0, 255, 0), thickness=cv2.FILLED)

        return contour_copy
    
    def get_channels(self):
        '''Identifies active electrode channels based on heatmap with contour.'''

        if not hasattr(self, 'heatmap'):  # check to see if the pre-requistite method is called
            raise RuntimeError("Contours not detected. Call get_contours() before get_channels().")
        elif not hasattr(self, 'counts_array'):
            raise RuntimeError("Heatmap not generated. Call get_heatmap() before get_channels().")
        
        mask = np.all(self.heatmap == [0, 255, 0], axis=-1) 
        coords = np.column_stack(np.where(mask))
        cleaned_heatmap = np.zeros((64, 64))
        for point in coords:
            x, y = point
            cleaned_heatmap[x][y] = self.counts_array[x][y]
            self.channels.append(64*x+y)
            # coordinate conventions differ between image and heatmaps (i.e., x and y are flipped)
        cleaned_heatmap[0][1] = self.counts_array[0][1]
        self.channels.append(64*0+1)
        self.channels.sort()

        # Mask and handle low values
        mask = cleaned_heatmap == 0
        counts_masked = ma.masked_array(cleaned_heatmap, mask=mask)
        counts_masked[counts_masked < 1] = 1

        vmin = cleaned_heatmap.min()
        vmax = cleaned_heatmap.max()

        # Plot heatmap
        fig = plt.Figure(figsize=(64, 64))
        ax = fig.add_subplot(1, 1, 1)

        heatmap = sns.heatmap(counts_masked, cmap='viridis', norm=LogNorm(vmin=vmin, vmax=vmax))
        cbar = heatmap.collections[0].colorbar
        cbar.ax.minorticks_off()

        # Set x and y ticks every 10 positions
        xticks = np.arange(0, 64, 10)
        yticks = np.arange(0, 64, 10)

        ax.set_xticks(xticks)
        ax.set_yticks(yticks)

        ax.set_xticklabels(xticks, rotation=45, ha='right')
        ax.set_yticklabels(yticks)

        plt.tight_layout()
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
    
    def to_mat(self, savePath, time_end=750):
        '''Convert and format data to a MAT file'''

        if any(not hasattr(self, attr) for attr in ['spikeDataChIdxs', 'spikeDataTimestamps', 'offsetValue', \
                                                    'spikeDataWaveforms', 'waveformLength', 'dacFactor']):  # check to see if the pre-requistite method is called
            raise RuntimeError("Variables not loaded. Call get_var() before to_mat().")
        
        # Check if offset is computed
        elif not hasattr(self, 'offset'):
            self.offset = 0
            print("Offset not computed. Converting without alignment")
        else:
            print(f"Using computed time offset: {self.offset}")
        
        print("Converting to MAT file format................")
        
        waveformData, timeData = {}, {}

        for ch in self.channels:
            waveformData[ch] = []
            timeData[ch] = []
        for idx, ch in enumerate(self.spikeDataChIdxs):
            if not self.channels or ch in self.channels:  # not self.channels checks if an image is given
                if ch not in waveformData:                # ch in self.channels checks if image is given and channels with activity are kept
                    waveformData[ch] = []
                    timeData[ch] = []
                
                time_s = (self.spikeDataTimestamps[idx]/self.samplingRate) - self.offset  # in seconds
                waveform = self.spikeDataWaveforms[idx * self.waveformLength : (idx + 1) * self.waveformLength]
                spikemV = [self.offsetValue + i * self.dacFactor for i in waveform] # convert digital signal to microvolt
                
                waveformData[ch].append(spikemV)  # store both!
                timeData[ch].append(time_s)

        # remove empty lists
        waveformData = {k:(np.zeros(self.waveformLength) if not v else v) for k,v in waveformData.items()}
        timeData = {k:(np.zeros(self.waveformLength) if not v else v) for k,v in timeData.items()}

        keys = list(waveformData.keys())
        spikeArray, timeArray = [], []
        for i in range(len(keys)):  
            spikeArray.append(np.asarray(waveformData[keys[i]], dtype=np.float64))
            arr = np.asarray(timeData[keys[i]], dtype=np.float64)
            timeArray.append(arr.reshape(-1, 1))

        # Format list to numpy column vector
        spikeArray = np.array(spikeArray, dtype=object).reshape(-1, 1)
        timeArray = np.array(timeArray, dtype=object).reshape(-1, 1)
        channels_arr = np.array(keys, dtype=np.float64).reshape(-1, 1)

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
    
    def run_auto(self, savePath, bxr_path, img_path, flag, threshold=25):
        self.read_files(bxr_path, img_path)
        self.get_var()
        self.get_heatmap(savePath)
        if flag == 0:
            self.select_landmark()
            self.transform()
            self.get_contours(threshold)
            self.get_coords()
        self.get_channels()
        if self.align_flag:
            self.align_time()
        self.to_mat(savePath, time_end=760)
    
    def run_manual(self, savePath, bxr_path, img_path, flag, threshold=25):
        self.read_files(bxr_path, img_path)
        self.get_var()
        self.get_heatmap(savePath)
        if flag == 0:
            self.select_landmark()
            self.transform()
            self.draw_contours()
        self.get_channels()
        if self.align_flag:
            self.align_time()
        self.to_mat(savePath, time_end=760)
    
    def run_all(self, savePath, bxr_path):
        self.read_files(bxr_path, img_path="")
        self.get_var()
        self.get_heatmap(savePath)
        if self.align_flag:
            self.align_time()
        self.to_mat(savePath, time_end=760)

if __name__ == '__main__':
    # read input from the user
    save_path = input("Enter output path: ")
    f_type = input("1 - Only .bxr file\n2 - Automated selection \n3 - Manual selection\nEnter 1, 2, or 3: ")
    files = input('Enter or drag file(s) : ')

    if f_type.isnumeric():
        f_type = int(f_type)
    else:
        print("Invalid input. Please enter numeric values only.")
        exit()

    files = files.split()
    flag = len(files)
    temp = set(itertools.combinations(files, 2))
    file_pairs = [combi for combi in temp if any(pathlib.Path(path).suffix.lower() in {".jpg", ".jpeg", ".png"} for path in combi)]
    si = MEAPipeline()

    if f_type == 1:
        si.run_all(savePath=save_path, bxr_path=files[0])
        # profile_algorithm(si.run_all, savePath=save_path, bxr_path=files[0])
        exit()
    elif f_type == 2:
        func = si.run_auto
    else:
        func = si.run_manual

    for idx, (path1, path2) in enumerate(file_pairs):
        if pathlib.Path(path1).suffix.lower() == ".bxr":
            bxr_path, img_path = path1, path2
        else:
            bxr_path, img_path = path2, path1
        func(savePath=save_path, bxr_path=bxr_path, img_path=img_path, flag=idx)
        # profile_algorithm(func, savePath=save_path, bxr_path=bxr_path, img_path=img_path, flag=idx)
