from pathlib import Path
import cv2, glob
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
from sklearn.neighbors import NearestNeighbors
from itertools import combinations

DIR = "C:\\Users\\Admin\\UniBE\\data\\images\\no_bg\\*.png"
paths = [f for f in glob.glob(DIR)]
graphs = []

# for path in paths:
for i in range(len(paths)):
    path = Path(paths[i])
    file = path.name

    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    im = img[:,:,2].copy()
    im = cv2.medianBlur(im, ksize=3)
    plt.imshow(im)
    plt.axis('off')

    bg = img[:,:,0].copy()
    g = cv2.medianBlur(bg, ksize=101)
    plt.imshow(bg)
    plt.axis('off')

    signal = cv2.subtract(im, bg)
    #imshow(signal)
    signal = (signal / signal.max() * 255).astype(np.uint8)
    plt.imshow(signal)
    plt.axis('off')

    smooth = cv2.GaussianBlur(signal, ksize=None, sigmaX=2)
    plt.imshow(smooth)
    plt.axis('off')

    print(smooth.min(), smooth.max(), smooth.mean())

    valmask = (smooth > 150)
    plt.imshow(valmask)
    plt.axis('off')

    dilated = cv2.dilate(smooth, np.ones((3,3), np.uint8))
    plt.imshow(dilated, cmap='gray')
    plt.axis('off')

    peakmask = (smooth == dilated)
    plt.imshow(peakmask, cmap='gray')
    plt.axis('off')

    blobs = (valmask & peakmask)
    # merge peaks that should be in the same blob
    #blobs = cv.dilate(blobs.astype('u1'), kernel=None, iterations=10)
    blobs = cv2.morphologyEx(blobs * np.uint8(255), cv2.MORPH_DILATE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11,11)))
    blobs = blobs.astype(bool)
    plt.imshow(blobs)
    plt.axis('off')

    (nlabels, labelmap, stats, centroids) = cv2.connectedComponentsWithStats(blobs.astype(np.uint8))
    print(nlabels-1, "components")

    # canvas = cv2.cvtColor(signal, cv2.COLOR_GRAY2BGR)
    for pt in centroids[1:]:
        cv2.circle(signal, center=pt.astype(int), radius=20, color=(255,255,0), thickness=2)
    plt.imshow(signal)
    plt.axis('off')

    # KNN map
    neigh = NearestNeighbors(n_neighbors=5+1, metric='euclidean')
    neigh.fit(centroids[1:])
    distances, indices = neigh.kneighbors(centroids[1:])

    G = nx.Graph()
    # Add nodes
    for i, point in enumerate(centroids[1:]):
        G.add_node(i, pos=point)

    # Add edges
    for i, neighbours in enumerate(indices):
        for neighbour in neighbours[1:]:  # Skip first index --> skip self (the point itself)
            if not G.has_edge(i, neighbour):
                G.add_edge(i, neighbour)
    
    # Collect all the graphs
    graphs.append(G)

    pos = nx.get_node_attributes(G, 'pos')

    plt.figure(2)
    img_rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    plt.imshow(img_rgb)

    nx.draw(G, pos, node_size=20, node_color='none', edgecolors='red', edge_color='green', linewidths=1)
    plt.title(f"{file}")
    # plt.gca().invert_yaxis()
    plt.savefig(file, bbox_inches='tight')
    plt.show()
