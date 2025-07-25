import cv2, glob, math
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
from pathlib import Path
from sklearn.neighbors import NearestNeighbors

DIR = "C:\\Users\\Admin\\UniBE\\data\\images\\no_bg\\*.png"
paths = [f for f in glob.glob(DIR)]
graphs, images, positions, filenames = [], [], [], []

# for path in paths:
for i in range(len(paths)):
    path = Path(paths[i])
    file = path.name

    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    im = img[:,:,2].copy()
    im = cv2.medianBlur(im, ksize=3)
    # plt.imshow(im)
    # plt.axis('off')

    bg = img[:,:,0].copy()
    g = cv2.medianBlur(bg, ksize=101)
    # plt.imshow(bg)
    # plt.axis('off')

    signal = cv2.subtract(im, bg)
    #imshow(signal)
    signal = (signal / signal.max() * 255).astype(np.uint8)
    # plt.imshow(signal)
    # plt.axis('off')

    smooth = cv2.GaussianBlur(signal, ksize=None, sigmaX=2)
    # print(smooth.min(), smooth.max(), smooth.mean())

    valmask = (smooth > 150)
    # plt.imshow(valmask)
    # plt.axis('off')

    dilated = cv2.dilate(smooth, np.ones((3,3), np.uint8))
    # plt.imshow(dilated, cmap='gray')
    # plt.axis('off')

    peakmask = (smooth == dilated)
    # plt.imshow(peakmask, cmap='gray')
    # plt.axis('off')

    blobs = (valmask & peakmask)
    # merge peaks that should be in the same blob
    #blobs = cv.dilate(blobs.astype('u1'), kernel=None, iterations=10)
    blobs = cv2.morphologyEx(blobs * np.uint8(255), cv2.MORPH_DILATE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11,11)))
    blobs = blobs.astype(bool)
    # plt.imshow(blobs)
    # plt.axis('off')

    (nlabels, labelmap, stats, centroids) = cv2.connectedComponentsWithStats(blobs.astype(np.uint8))
    # print(nlabels-1, "components")

    for pt in centroids[1:]:
        cv2.circle(signal, center=pt.astype(int), radius=20, color=(255,255,0), thickness=2)
    # plt.imshow(signal)
    # plt.axis('off')

    # KNN map
    neigh = NearestNeighbors(n_neighbors=5+1, metric='euclidean')
    neigh.fit(centroids[1:])
    _, indices = neigh.kneighbors(centroids[1:])

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
    img_rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    images.append(img_rgb)  # or img_rgb if preferred
    filenames.append(file)

    # plt.figure(2)
    # img_rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    # plt.imshow(img_rgb)

    # pos = nx.get_node_attributes(G, 'pos')
    # nx.draw(G, pos, node_size=20, node_color='none', edgecolors='red', edge_color='green', linewidths=1)
    # plt.title(f"{file}")
    # # plt.gca().invert_yaxis()
    # # plt.savefig(file, bbox_inches='tight')
    # # plt.show()

match = []
max_dist = 100  # max allowed distance to consider a match

for t in range(len(graphs) - 1):
    G_t = graphs[t]
    G_t1 = graphs[t + 1]

    img, file = images[t], filenames[t]

    pos_t = nx.get_node_attributes(G_t, 'pos')
    pos_t1 = nx.get_node_attributes(G_t1, 'pos')

    unmatched_t1 = set(pos_t1.keys())  # nodes available for matching in t+1

    for n, coords in pos_t.items():
        x1, y1 = coords

        # Find nearest node in t+1 among unmatched nodes
        nearest_node = None
        min_dist = float('inf')

        for n1 in unmatched_t1:
            x2, y2 = pos_t1[n1]
            dist = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
            if dist < min_dist and dist <= max_dist:
                min_dist = dist
                nearest_node = n1

        if nearest_node is not None:
            match.append((n, nearest_node))  # record match as a tuple (node_t, node_t+1)
            unmatched_t1.remove(nearest_node)  # remove to ensure one-to-one mapping

    plt.figure(2)
    plt.imshow(img)

    # Separate matched and unmatched nodes
    matched_nodes = {n for n, n1 in match}  # nodes in G_t matched to G_t1
    matched_pos = {n: pos_t[n] for n in matched_nodes if n in pos_t}
    unmatched_pos = {n: p for n, p in pos_t.items() if n not in matched_nodes}

    color_map = []
    for idx in pos_t:
        if idx in list(matched_pos.keys()):
            color_map.append('green')  
        else:
            color_map.append('red') 

    nx.draw(G_t, pos_t, node_size=20, node_color=color_map, linewidths=1)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(file, bbox_inches='tight')
    plt.show()
