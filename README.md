# Spike2Mat

This repository contains tools for spike sorting and visualization using electrophysiological data. It includes both exploratory scripts and a complete Python-based application for processing and analyzing MEA (Multi-Electrode Array) recordings.

---

## 📦 Setup Instructions

### 1. Install Python  
Make sure Python is installed on your system. You can download the latest version from:  
🔗 [https://www.python.org/downloads/](https://www.python.org/downloads/)

### 2. Clone or download the repository
Optional: Download the repository by clicking the green ‘Code’ button.
```bash
git clone https://github.com/diiivyaa/spike-sort.git
```

### 3. Create and activate a virtual environment

First, create a virtual environment using `venv`:

```bash
python -m venv venv
```


**For Windows:**

```bash
venv\Scripts\activate
```

**For macOS/Linux:**

```bash
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

---
## 🗂️ Project Structure

| Path                          | Type   | Description                                             |
|-------------------------------|--------|---------------------------------------------------------|
| `pike-sort/`                  | Folder | Root project directory                                  |
| ├── `3Brain/`                 | Folder | Exploratory data analysis and herding spikes            |
| ├── `src/`                    | Folder | Main source code directory                              |
| │ ├── `app/`                  | Folder | Application scripts and assets                          |
| │ │ ├── `MEA_pipeline.py`     | File   | App-specific processing pipeline                        |
| │ │ ├── `App.py`              | File   | Main application script with UI and logic               |
| │ │ ├── `progressBar.py`      | File   | Progress bar utility for the app                        |
| │ │ └── `app.spec`            | File   | PyInstaller specification file                          |
| │ ├── `brw/`                  | Folder | Exploratory/debugging scripts for BRW files             |
| │ ├── `bxr/`                  | Folder | Exploratory/debugging scripts for BXR files             |
| │ ├── `cell_tracking/`        | Folder | Cell tracking scripts and results (images)              |
| │ ├── `variation/`            | Folder | Computes variation between selected contour channels    |
| │ └── `MEA_pipeline.py`       | File   | Standalone pipeline script (outside of app context)     |
| └── `requirements.txt`        | File   | Python dependencies 

---
## ⚙️ Build the Application
To package the app using PyInstaller:

```bash
pyinstaller src/app/app.spec
```

---
## 🧪 Notes

- Use the `3Brain/` folder for testing and exploratory data analysis, especially for herding spikes.
- The GUI app is built using `App.py` in the `src/app/` directory.
- The `MEA_pipeline.py` script in `src/` can be used independently for data processing outside of the app context.

---
## 🧫 Cell Tracking

### 1. Trackpy  
Trackpy is used for particle tracking and is best installed via Anaconda. 

Follow the setup guide here: [Trackpy Installation Guide](https://soft-matter.github.io/trackpy/v0.7/installation.html). Run the Jupyter notebook `trackpy.ipynb` using the configured conda environment.

### 2. K-Nearest Neighbour Tracking  
This method combines K-Nearest Neighbour tracking (using Euclidean distance) with per-frame graph construction to analyse spatial relationships.

Run `spatial_map.py` **in the virtual environment (venv)** and not in the conda environment.
