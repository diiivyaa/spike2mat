import os, sys, pathlib, itertools
from PIL import Image
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, \
QStackedWidget, QRadioButton, QButtonGroup, QLabel, QSizePolicy, QScrollArea, QLineEdit, QGroupBox, QFrame
from PySide6.QtGui import QFontDatabase, QIcon, QFont, QIntValidator, QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, QSize, Slot, QThread, QObject, Signal, Slot

from MEA_pipeline import MEAPipeline
from progressBar import CustomProgressBar

def resource_path(relative_path):
    """Get path to bundled resource, whether in dev or in PyInstaller .exe"""
    try:
        base_path = sys._MEIPASS  # PyInstaller temporary path
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))  # dev mode
        # base_path = os.path.join(base_path, "assets")

    return os.path.join(base_path, relative_path)

class ImportFile(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.bxr_path = None
        self.img_path = None

        layout = QVBoxLayout()
        container = QWidget()

        file_box_layout = QHBoxLayout()
        file_box_layout.setContentsMargins(20, 0, 20, 0)
        file_box_layout.setSpacing(10)

        # Choose File Button
        self.upload_button = QPushButton("Import file(s)")
        self.upload_button.setFixedSize(100, 35)
        self.upload_button.clicked.connect(self.import_func)

        # Scrollable file label
        self.file_label = QLabel("No file(s) selected")
        self.file_label.setStyleSheet("color: #555; padding: 5px;")
        self.file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.file_label.setWordWrap(True)

        # Scroll area to contain file label
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(60)
        self.scroll_area.setWidget(self.file_label)
        self.scroll_area.setStyleSheet("border: none; background-color: #ffffff;")

        # File Label
        file_box_layout.addWidget(self.upload_button)
        file_box_layout.addWidget(self.scroll_area)

        container_layout = QVBoxLayout()
        container_layout.addSpacing(20)
        heading = QLabel("Upload files. Accepted file extensions are .bxr, .jpg, .jpeg and .png")
        heading.setStyleSheet("font-size: 14px; color: #333; padding: 8px;")
        container_layout.addWidget(heading, alignment=Qt.AlignCenter|Qt.AlignTop)
        container_layout.addSpacing(20)
        container_layout.addLayout(file_box_layout)
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(lambda: controller.show_frame("Save dir"))
        self.next_button.setEnabled(False)
        container_layout.addSpacing(20)
        container_layout.addWidget(self.next_button)
        container_layout.addStretch()

        container.setLayout(container_layout)
        container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 180);  /* white with transparency */
                border: 1px solid #ccc;
                border-radius: 12px;
                padding: 10px;}
            QPushButton {
                background-color: #3532d1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                margin: 0 5px;}
            QPushButton:hover {
                background-color: white;
                color: #3532d1;}""")
        container.setFixedSize(700, 250)

        layout.addWidget(container, alignment=Qt.AlignCenter)
        self.setLayout(layout)

    def import_func(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select files", "", "Images and BXR (*.bxr *.jpeg *.jpg *.png)")
        self.controller.bxr_path, self.controller.img_path = None, None
        if files:
            self.controller.is_more_than_two_files = len(files)
            self.controller.dir_path  = pathlib.Path(files[0]).parent  # Get parent folder

            filenames_display = "\n".join([f"• {os.path.basename(path)}" for path in files])
            self.file_label.setText(f"{len(files)} file(s) selected:\n{filenames_display}")
            self.file_label.setToolTip("\n".join(files))
            self.controller.obj.input_flag = len(files)

            if len(files) == 1 and pathlib.Path(files[0]).suffix.lower() == ".bxr":  # If only one bxr file is given
                self.controller.bxr_path, self.controller.img_path = files[0], ""
                self.controller.file_pairs = [(self.controller.bxr_path, self.controller.img_path)]
            else:  # for one image file and 1 or more bxr files
                temp = set(itertools.combinations(files, 2))    # Get all pair combinations of files
                self.controller.file_pairs = [combi for combi in temp if any(pathlib.Path(path).suffix.lower() in {".jpg", ".jpeg", ".png"} for path in combi)]
                # Keep only the pairs with an image file

            for (path1, path2) in self.controller.file_pairs:  # Run through all given files to check if all are valid
                if pathlib.Path(path1).suffix.lower() == ".bxr":
                    self.controller.bxr_path, self.controller.img_path = path1, path2
                else:
                    self.controller.bxr_path, self.controller.img_path = path2, path1
            
                self.controller.obj.read_files(self.controller.bxr_path, self.controller.img_path)
                self.controller.offset_flag = self.controller.obj.get_var()  # Use the last valid file to check for the time channel
        
        self.next_button.setEnabled(True)
        self.controller.pages["Save dir"].file_label.setText(str(self.controller.dir_path))
        
class saveDir(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout()
        container = QWidget()
        container_layout = QVBoxLayout()

        file_dir = QHBoxLayout()
        save_button = QPushButton("Select directory to save output files")
        save_button.setFixedSize(250, 40)
        save_button.clicked.connect(self.process)
        file_dir.addWidget(save_button)

        self.file_label = QLabel("No file(s) selected")
        self.file_label.setStyleSheet("color: #555; padding: 5px;")
        self.file_label.setFixedHeight(50)
        self.file_label.setWordWrap(True)
        file_dir.addWidget(self.file_label)
        container_layout.addLayout(file_dir)

        params = QGroupBox("Parameters")
        params_layout = QVBoxLayout()
        qn1_layout = QHBoxLayout()
        qn1_layout.addSpacing(10)
        time_label = QLabel("Enter end duration (s):")
        time_label.setFixedSize(155, 40)
        self.time_end = QLineEdit(container)
        self.time_end.setPlaceholderText("Default value is 750s")
        self.time_end.setValidator(QIntValidator(1, 999, self))
        qn1_layout.addWidget(time_label)
        qn1_layout.addWidget(self.time_end)

        qn2_layout = QHBoxLayout()
        qn2_layout.addSpacing(10)
        self.offset_label = QLabel("Enter offset value (s):")
        self.offset_label.setFixedSize(155, 40)
        self.offset = QLineEdit(container)
        self.offset.setPlaceholderText("Default is 0")
        self.offset.setValidator(QIntValidator(1, 999, self))
        qn2_layout.addWidget(self.offset_label)
        qn2_layout.addWidget(self.offset)
        self.offset_label.hide()
        self.offset.hide()

        params_layout.addLayout(qn1_layout)
        params_layout.addLayout(qn2_layout)
        params.setLayout(params_layout)
        container_layout.addWidget(params)
        
        nav_layout = QHBoxLayout()
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: controller.show_frame("File type"))
        nav_layout.addWidget(back_button)

        next_button = QPushButton("Next")
        nav_layout.addWidget(next_button)
        next_button.clicked.connect(self.next_clicked)
        container_layout.addSpacing(10)
        container_layout.addLayout(nav_layout)
        container.setLayout(container_layout)

        container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 180);  /* white with transparency */
                border: 1px solid #ccc;
                border-radius: 12px;
                padding: 10px;}
            QPushButton {
                background-color: #3532d1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                margin: 0 5px;}
            QPushButton:hover {
                background-color: white;
                color: #3532d1;}
            QLabel {
                color: black;}
            QLineEdit{
                color: black;}
            QGroupBox {
                background-color: transparent;
                font-weight: normal;
                border: 1px solid lightgray;
                border-radius: 5px;
                margin-top: 6px;}
            QGroupBox::title {
                color: balck;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                background-color: transparent;}""")
        container.setFixedSize(700, 250)

        layout.addWidget(container, alignment=Qt.AlignCenter)
        self.setLayout(layout)
    
    def update_offset(self):
        if self.controller.offset_flag:
            self.controller.align_time = self.controller.obj.align_time  # Store the function and call it during processing
            self.offset_label.hide()
            self.offset.hide()
        else:
            self.offset_label.show()
            self.offset.show()
            self.controller.align_time = None

    def process(self):
        self.controller.dir_path = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if self.controller.dir_path:
            self.file_label.setText(self.controller.dir_path)
    
    def next_clicked(self):
        self.controller.obj.get_heatmap(self.controller.dir_path)
        # Set default values
        offset = self.offset.text()
        time = self.time_end.text()

        self.controller.offset = int(offset) if offset else 0
        self.controller.time = int(time) if time else 760
    
        print(f"Input flag: {self.controller.obj.input_flag}")
        if self.controller.obj.input_flag > 1:
            self.controller.show_frame("Contour detection")
        else:  # If only bxr file --> go straight to processing
            self.controller.show_frame("Loading")
            self.controller.pages["Loading"].start_work()

class OptionSelect(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout()
        container = QWidget()
        container_layout = QVBoxLayout()

        self.selection = "1" # var to hold the option selected

        label = QLabel("Choose selection method:")
        container_layout.addWidget(label)

        self.radio_group = QButtonGroup(self)
        self.radio_group.setExclusive(False)
        self.auto_radio = QRadioButton("Automated selection")
        self.manual_radio = QRadioButton("Manual selection")

        self.radio_group.addButton(self.auto_radio, id=1)
        self.radio_group.addButton(self.manual_radio, id=2)

        container_layout.addWidget(self.auto_radio)
        # Ask for threshold input if automatic detection is selected
        self.thresh = QLineEdit(container)
        self.thresh.setPlaceholderText("Enter threshold value otherwise default is 25")
        self.thresh.setValidator(QIntValidator(1, 999, self))
        container_layout.addWidget(self.thresh)
        self.thresh.hide()
        container_layout.addWidget(self.manual_radio)
        self.radio_group.idClicked.connect(self.check)

        nav_layout = QHBoxLayout()
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: self.controller.show_frame("Save dir"))
        nav_layout.addWidget(back_button)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.process)
        nav_layout.addWidget(self.next_button)
        container_layout.addLayout(nav_layout)
        container.setLayout(container_layout)

        container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 180);  /* white with transparency */
                border: 1px solid #ccc;
                border-radius: 12px;
                padding: 10px;}
            QPushButton {
                background-color: #3532d1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                margin: 0 5px;}
            QPushButton:hover {
                background-color: white;
                color: #3532d1;}
            QLabel {
                color: black;}
            QRadioButton {
                color: black;}
            QLineEdit {
                color:black}""")
        container.setFixedSize(700, 250)

        layout.addWidget(container, alignment=Qt.AlignCenter)
        self.setLayout(layout)

    # Check the radio selecction
    def check(self):
        radio_id = self.radio_group.checkedId()
        self.threshold = 25  # default
        if radio_id == 1:
            self.auto_radio.setChecked(True)
            self.manual_radio.setChecked(False)
            self.controller.contours = self.controller.obj.get_contours # Collect the correct methods from MEAPipeline
            self.controller.helper = self.controller.obj.get_coords
            self.thresh.show() # Show the input to get threshold
            self.thresh.returnPressed.connect(self.process)
        if radio_id == 2:
            self.auto_radio.setChecked(False)
            self.manual_radio.setChecked(True)
            self.thresh.hide() # Hide the input to get threshold
            self.controller.contours = self.controller.obj.draw_contours
            self.controller.helper = None

    def process(self):
        self.next_button.setEnabled(False)  # disable next button
        # Check if threshold line edit is visible
        if self.thresh.isVisible():
            text = self.thresh.text()
            if text:
                self.controller.threshold = int(text)
        
        self.clear()

        self.controller.show_frame("Loading")
        self.controller.pages["Loading"].start_work()
        
        self.next_button.setEnabled(True)  # enable next button
    
    def clear(self):
        self.auto_radio.setChecked(False)
        self.manual_radio.setChecked(False)

class Loading(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self.layout = QVBoxLayout()
        container = QWidget()
        container_layout = QVBoxLayout()

        spin_layout = QVBoxLayout()
        spin_layout.setSpacing(0)
        spin_layout.setContentsMargins(0, 0, 0, 0)

        self.spinner = QSvgWidget(resource_path("assets/830.svg"))
        self.spinner.setFixedSize(100, 100)

        self.label = QLabel("Processing, please wait...")
        self.label.setStyleSheet("font-size: 14px; color: #333; padding: 8px;")

        self.home_button = QPushButton("Home")
        self.home_button.clicked.connect(self.go_home)
        self.home_button.setVisible(False)

        self.cancel_button = QPushButton("Cancel")
        self.home_button.clicked.connect(self.cancel_worker)
        self.cancel_button.setVisible(False)

        spin_layout.addSpacing(20)
        spin_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        spin_layout.addSpacing(15)
        spin_layout.addWidget(self.label, alignment=Qt.AlignCenter)

        container_layout.addLayout(spin_layout)
        container_layout.addWidget(self.home_button)
        container_layout.addWidget(self.cancel_button)
        container.setLayout(container_layout)

        container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 180);  /* white with transparency */
                border: 1px solid #ccc;
                border-radius: 12px;
                padding: 10px;}
            QPushButton {
                background-color: #3532d1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                margin: 0 5px;}
            QPushButton:hover {
                background-color: white;
                color: #3532d1;}
            QSvgWidget {
                background-color: transparent;
                border: 0px;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;}""")
        container.setFixedSize(700, 250)

        self.layout.addWidget(container, alignment=Qt.AlignCenter)
        self.setLayout(self.layout)

        # Variables to track progress
        self.current_index = 0
        self.thread = None
        self.worker = None

    @Slot()
    def start_work(self):
        self.label.setText("Starting processing...")
        self.home_button.setVisible(False)
        self.cancel_button.setEnabled(True)

        self.file_pairs = self.controller.file_pairs
        self.save_path = self.controller.dir_path
        self.time_end = self.controller.time
        self.offset = self.controller.offset

        self.num_times = self.controller.obj.input_flag - 1 if self.controller.obj.input_flag > 1 else self.controller.obj.input_flag
        self.current_index = 0
        self.start_next_worker()

    def start_next_worker(self):
        self.spinner.show()
        if self.current_index >= self.num_times:
            self.label.setText("All files processed!")
            self.spinner.hide()
            self.home_button.setVisible(True)
            self.cancel_button.setVisible(False)
            return

        if self.controller.obj.input_flag > 1:
            path1, path2 = self.file_pairs[self.current_index]
            if pathlib.Path(path1).suffix.lower() == ".bxr":
                bxr_path, img_path = path1, path2
            else:
                bxr_path, img_path = path2, path1
        else:
            bxr_path, img_path = self.controller.bxr_path, self.controller.img_path

        self.label.setText(f"Processing {self.current_index+1} of {self.num_times} data file(s)")

        # Run main thread first (methods for all types of input)
        self.controller.obj.read_files(bxr_path, img_path)
        self.controller.obj.get_var()
        self.controller.obj.get_heatmap(self.save_path)

        if self.controller.obj.input_flag > 1:
            if self.current_index == 0:
                # Only run these methods when image is given and for the first file pair
                self.controller.obj.select_landmark()
                self.controller.obj.transform()
                self.controller.contours()
                if self.controller.helper:
                    self.controller.helper()
            self.controller.obj.get_channels()  # Get channels for every file 

        # Now start a thread JUST for 'to_mat'. Why? to keep the GUI responsive during processing
        self.thread = QThread()
        self.worker = Worker(self.controller, self.save_path, self.time_end, self.offset)
        self.worker.moveToThread(self.thread)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.result.connect(self.display_result)
        self.worker.cancelled.connect(self.handle_cancelled)

        self.thread.started.connect(self.worker.do_work)
        self.thread.finished.connect(self.on_thread_finished)

        self.thread.start()

    def on_thread_finished(self):
        self.current_index += 1
        self.start_next_worker()

    @Slot(str)
    def display_result(self, message):
        self.spinner.hide()
        self.label.setText(message)
        self.home_button.setVisible(True)
        self.cancel_button.setVisible(False)

    def cancel_worker(self):
        if self.worker:
            self.worker.cancel()
            self.label.setText("Cancelling...")

    def handle_cancelled(self):
        self.label.setText("Cancelled by user")
        self.home_button.setVisible(True)
        self.cancel_button.setEnabled(False)
    
    def reset(self):
        self.spinner.show()
        self.label.setText("Processing, please wait...")
        self.home_button.setVisible(False)
        self.cancel_button.setVisible(True)
        self.current_index = 0
    
    def go_home(self):
        self.reset()
        self.controller.obj = MEAPipeline()
        self.controller.show_frame("File type")

class Worker(QObject):
    finished = Signal()
    cancelled = Signal()
    result = Signal(str)

    def __init__(self, pipeline, save_path, time_end, offset):
        super().__init__()
        self.pipeline = pipeline
        self.save_path = save_path
        self.time_end = time_end
        self.offset = offset
        self._is_interrupted = False

    @Slot()
    def do_work(self):
        if self._is_interrupted:
            self.cancelled.emit()
            self.finished.emit()
            return
        try:
            if self.pipeline.align_time:
                self.pipeline.align_time()
                self.pipeline.obj.to_mat(self.save_path, self.time_end)
            else:
                self.pipeline.obj.to_mat(self.save_path, self.time_end, self.offset)
            self.result.emit("Processing done for current file")
        except Exception as e:
            self.result.emit(f"Error in thread: {e}")

        self.finished.emit()

    def cancel(self):
        self._is_interrupted = True

class stepBox(QFrame):
    def __init__(self, step_number, description, image_path=None, desc_path=None):
        super().__init__()
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("border-radius: 12px; border: 1px solid #ddd; background-color: #fff; padding: 16px; margin-bottom: 20px;")

        layout = QVBoxLayout()

        # Step and description
        step_layout = QHBoxLayout()
        step_label = QLabel(f"<h2>Step {step_number}</h2>")
        step_label.setTextFormat(Qt.TextFormat.RichText)
        step_layout.addWidget(step_label)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        step_layout.addWidget(desc_label)

        step_layout.setStretch(0, 1)
        step_layout.setStretch(1, 2)
        layout.addLayout(step_layout)

        # Image layout (side-by-side)
        if image_path or desc_path:
            image_layout = QVBoxLayout()
            
            if image_path:
                image_label = QLabel()
                pixmap = QPixmap(image_path)
                pixmap.setDevicePixelRatio(app.devicePixelRatio()) 
                image_label.setPixmap(pixmap)
                image_label.setAlignment(Qt.AlignmentFlag.AlignTop)
                image_layout.addWidget(image_label)

            if desc_path:
                desc_image_label = QLabel()
                desc_pixmap = QPixmap(desc_path)
                desc_pixmap.setDevicePixelRatio(app.devicePixelRatio())
                desc_image_label.setPixmap(desc_pixmap)
                desc_image_label.setAlignment(Qt.AlignmentFlag.AlignTop)
                image_layout.addWidget(desc_image_label)

            layout.addLayout(image_layout)

        self.setLayout(layout)

class learnMore(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Guide")
        self.setStyleSheet("background-color: white; color: black;")
        self.setGeometry(100, 100, 1100, 600)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Container widget inside scroll area
        container = QWidget()
        scroll.setWidget(container)

        # Layout for the container
        layout = QVBoxLayout(container)

        header = QLabel("<h1>User Guide</h1><p>A guide to help you navigate Spike2Mat in just 4 steps.</p>")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setWordWrap(True)
        layout.addWidget(header)

        layout.addWidget(stepBox(1, 'Upload supported files: .bxr for data, and .jpeg, .jpg, or .png for images.', resource_path("assets/step1.png")))
        layout.addWidget(stepBox(2, 'Enter the output path. Specify the end time and offset manually if time channel (1, 2) is missing.', resource_path("assets/step2.png")))
        layout.addWidget(stepBox(3, 'If an image is uploaded, select a contour detection method.', resource_path("assets/step3.png"), resource_path("assets/info.png")))
        layout.addWidget(stepBox(4, 'Wait for processing. The converted .mat file will be saved to the output path.'))

        layout.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

class MEAGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 960, 600)

        _id = QFontDatabase.addApplicationFont(resource_path("assets/fa-solid-900.ttf"))

        self.obj = MEAPipeline()
        self.stack = QStackedWidget()
        self.flag = False

        self.pages = {
            "File type": ImportFile(self),
            "Save dir": saveDir(self),
            "Contour detection": OptionSelect(self),
            "Loading": Loading(self)}
        
        for _, page in self.pages.items():
            self.stack.addWidget(page)
        
        title = QLabel("Spike2Mat")
        title.setStyleSheet("font-size: 25px; font-weight: bold; padding-left: 5px;")

        howTo_button = QPushButton('Learn more')
        howTo_button.setIcon(QIcon(resource_path("assets/icons8-help-50.png")))
        howTo_button.setIconSize(QSize(20, 20))
        howTo_button.setFont(QFont('Arial', 10, QFont.Bold))
        howTo_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 90);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px 16px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #3532d1;
            }""")
        howTo_button.setFixedSize(135, 45)
        howTo_button.clicked.connect(self.show_howTo)

        self.progressbar = CustomProgressBar()
        self.progressbar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.progressbar.setFixedSize(550,55) 
        self.progressbar.labels = ["File upload", "Parameters", "Contour detection", 'Results']

        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.addWidget(title, alignment=Qt.AlignLeft)
        h_layout.addWidget(self.progressbar, alignment=Qt.AlignCenter)
        h_layout.addWidget(howTo_button, alignment=Qt.AlignRight)

        # Create one central widget with vertical layout
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(header)
        layout.addWidget(self.stack)

        self.setCentralWidget(widget)
        self.show_frame("File type")

    def show_frame(self, name):
        page = self.pages.get(name)
        if page:
            if name == "Save dir":
                self.pages["Save dir"].update_offset()  # update offset visibility
            self.stack.setCurrentWidget(page)
            index = list(self.pages.keys()).index(name)
            self.progressbar.value = index
    
    def show_howTo(self):
        if not hasattr(self, 'learnMore') or not self.learnMore.isVisible():
            self.learnMore = learnMore()
            self.learnMore.show()
        else:
            self.learnMore.raise_()
            self.learnMore.activateWindow()

stylesheet = """MEAGui {
        background-image: url(%s); 
        background-repeat: no-repeat; 
        background-position: center;
    }""" % resource_path("assets\\7178736_11911.jpg").replace("\\", "/")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
    app.setStyleSheet(stylesheet)
    window = MEAGui()
    window.show()
    sys.exit(app.exec())