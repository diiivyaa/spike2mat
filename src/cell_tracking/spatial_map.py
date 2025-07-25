import cv2, glob, math, re
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
from pathlib import Path
from sklearn.neighbors import NearestNeighbors

DIR = "C:\\Users\\Admin\\UniBE\\data\\images\\no_bg\\*.png"
paths = [f for f in glob.glob(DIR)]
graphs, images, positions, filenames = [], [], [], []

# Construct KNN graph
for i in range(len(paths)):
    path = Path(paths[i])
    file = path.name
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    im = img[:,:,2].copy()
    im = cv2.medianBlur(im, ksize=3)

    bg = img[:,:,0].copy()
    g = cv2.medianBlur(bg, ksize=101)

    signal = cv2.subtract(im, bg)
    signal = (signal / signal.max() * 255).astype(np.uint8)

    smooth = cv2.GaussianBlur(signal, ksize=None, sigmaX=2)
    valmask = (smooth > 150)
    dilated = cv2.dilate(smooth, np.ones((3,3), np.uint8))
    peakmask = (smooth == dilated)

    blobs = (valmask & peakmask)
    # merge peaks that should be in the same blob
    #blobs = cv.dilate(blobs.astype('u1'), kernel=None, iterations=10)
    blobs = cv2.morphologyEx(blobs * np.uint8(255), cv2.MORPH_DILATE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11,11)))
    blobs = blobs.astype(bool)


    (nlabels, labelmap, stats, centroids) = cv2.connectedComponentsWithStats(blobs.astype(np.uint8))
    for pt in centroids[1:]:
        cv2.circle(signal, center=pt.astype(int), radius=20, color=(255,255,0), thickness=2)

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
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    images.append(img_rgb)
    filenames.append(file)

    # fig = plt.figure()
    # plt.imshow(img_rgb)

    # pos = nx.get_node_attributes(G, 'pos')
    # nx.draw(G, pos, node_size=20, node_color='none', edgecolors='red', edge_color='green', linewidths=1)
    # plt.title(f"{file}")
    # # plt.savefig(file, bbox_inches=None, pad_inches=0)
    # plt.show()

# Cell tracking
max_dist = 50  # max allowed distance to consider a match
global_id_counter = 0
tracks = {}  # global_id -> list of (frame_index, local_node_index)
node2global_id = [{} for _ in graphs]  # per frame: local_node_id -> global_id

# assign initial global IDs
G0 = graphs[0]
pos0 = nx.get_node_attributes(G0, 'pos')

for node in G0.nodes:
    gid = global_id_counter
    global_id_counter += 1
    # If the graph G0 (frame 0) has nodes with local IDs 4, 7, and 10 --> node2global_id = {4: 0, 7: 1, 10: 2}
    node2global_id[0][node] = gid
    tracks[gid] = [(0, node)]

# subsequent frames 
for t in range(1, len(graphs)):
    G_prev = graphs[t - 1]
    G_curr = graphs[t]
    pos_prev = nx.get_node_attributes(G_prev, 'pos')  # it is a dictionary where nodes are keys and coords are values
    pos_curr = nx.get_node_attributes(G_curr, 'pos')

    unmatched_curr = set(G_curr.nodes)  # all nodes are currently unmatched in a given graph

    for node_prev in G_prev.nodes:
        gid = node2global_id[t - 1][node_prev]  # get the unique id set previously 
        x1, y1 = pos_prev[node_prev]

        nearest_node = None
        min_dist = float('inf')  # set a tuned/realistic value depening on dataset

        for node_curr in unmatched_curr: # loops through the unmatched nodes against the current node in the outer loop
            x2, y2 = pos_curr[node_curr]
            dist = math.hypot(x1 - x2, y1 - y2)  # computes Euclidean distance equivalent to math.sqrt((x1-x2)**2+(y1-y1)**2)

            if dist < min_dist and dist <= max_dist:
                min_dist = dist
                nearest_node = node_curr

        if nearest_node is not None:
            # if match found → assign same global ID
            node2global_id[t][nearest_node] = gid
            tracks[gid].append((t, nearest_node))
            unmatched_curr.remove(nearest_node)

    # Assign new global IDs to unmatched nodes
    for node in unmatched_curr:
        gid = global_id_counter
        global_id_counter += 1
        node2global_id[t][node] = gid
        tracks[gid] = [(t, node)]

num_frames = len(graphs)
# Find IDs present in all frames
persistent_ids = [gid for gid, steps in tracks.items() if len({t for t, _ in steps}) == num_frames]

fig, axs = plt.subplots(1, num_frames, figsize=(15, 4))
for t in range(num_frames):
    G = graphs[t]
    pos = nx.get_node_attributes(G, 'pos')
    img = images[t]
    ax = axs[t]

    matched_nodes = []
    unmatched_nodes = []

    for node in G.nodes:
        gid = node2global_id[t].get(node)
        if gid in persistent_ids:
            matched_nodes.append(node)
        else:
            unmatched_nodes.append(node)
    
    ax.imshow(img, cmap='gray')
    nx.draw(G, pos, nodelist=matched_nodes, node_color='green', node_size=40, edgecolors='black', ax=ax)
    f_name = re.search(r"^(.*?20\d{2})", filenames[t]).group(1)
    ax.set_title(f_name)
    ax.axis('off')

plt.savefig("tracked_cells", bbox_inches=None, pad_inches=0)
plt.show()
