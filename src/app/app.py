import os, sys, pathlib
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, \
QStackedWidget, QRadioButton, QButtonGroup, QLabel, QSizePolicy, QScrollArea, QLineEdit
from PySide6.QtGui import QFontDatabase, QIcon, QFont, QIntValidator
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, QSize, Slot, Signal, QObject, QThread

from MEA_pipeline import MEAPipeline
from progressBar import CustomProgressBar

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))

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
        self.file_label = QLabel("No file chosen")
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
        heading = QLabel("Upload files. Accepted file extensions are .bxr, .brw, .jpg, .jpeg and .png")
        heading.setStyleSheet("font-size: 14px; color: #333; padding: 8px;")
        container_layout.addWidget(heading, alignment=Qt.AlignCenter|Qt.AlignTop)
        container_layout.addSpacing(20)
        container_layout.addLayout(file_box_layout)
        next_button = QPushButton("Next")
        next_button.clicked.connect(lambda: controller.show_frame("Save dir"))
        container_layout.addSpacing(20)
        container_layout.addWidget(next_button)
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
        files, _ = QFileDialog.getOpenFileNames(self, "Select files", "", "Images, BXR and BRW (*.bxr *.brw *.jpeg *.jpg *.png)")
        self.controller.bxr_path, self.controller.img_path = None, None
        if files:
            filenames_display = "\n".join([f"• {os.path.basename(path)}" for path in files])
            self.file_label.setText(f"{len(files)} file(s) selected:\n{filenames_display}")
            self.file_label.setToolTip("\n".join(files))
            for f_path in files:
                ext = pathlib.Path(f_path).suffix
                if ext == ".bxr":
                    self.controller.bxr_path = f_path
                elif ext == ".jpeg" or ext == ".jpg" or ext == ".png":
                    self.controller.img_path = f_path
                    self.controller.flag = True
                    print(self.controller.flag)
                else:
                    self.controller.img_path = ""
            self.controller.obj.read_files(self.controller.bxr_path, self.controller.img_path)
            self.controller.obj.get_var()
            
class savePath(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout()
        container = QWidget()
        container_layout = QVBoxLayout()

        save_button = QPushButton("Select directory to save output files")
        save_button.clicked.connect(self.process)
        container_layout.addWidget(save_button)

        nav_layout = QHBoxLayout()
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: controller.show_frame("File type"))
        nav_layout.addWidget(back_button)

        next_button = QPushButton("Next")
        nav_layout.addWidget(next_button)
        next_button.clicked.connect(self.next_clicked)
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
                color: #3532d1;}""")
        container.setFixedSize(700, 250)

        layout.addWidget(container, alignment=Qt.AlignCenter)
        self.setLayout(layout)

    def process(self):
        self.controller.dir_path = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if self.controller.dir_path:
            self.controller.obj.get_heatmap(self.controller.dir_path)
    
    def next_clicked(self):
        print(f"Flag value at click: {self.controller.flag}")
        if self.controller.flag:
            self.controller.show_frame("Contour detection")
        else:
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

        next_button = QPushButton("Next")
        next_button.clicked.connect(self.process)
        nav_layout.addWidget(next_button)
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

            self.func = self.controller.obj.get_contours # Collect the correct methods from MEAPipeline
            self.helper_func = self.controller.obj.get_coords
            self.channels_func = self.controller.obj.get_channels

            self.thresh.show() # Show the input to get threshold
            self.thresh.returnPressed.connect(self.process)
        if radio_id == 2:
            self.auto_radio.setChecked(False)
            self.manual_radio.setChecked(True)
            self.thresh.hide() # Hide the input to get threshold
            
            self.func = self.controller.obj.draw_contours
            self.channels_func = self.controller.obj.get_channels
     
    def process(self):
        # Always run these steps regardless of contour detection method
        self.controller.obj.select_landmark()
        self.controller.obj.transform()

        # Check which radio button is selected

        # Check if threshold line edit is visible
        if self.thresh.isVisible():
            text = self.thresh.text()
            if text:
                self.threshold = int(text)
                self.func(threshold=self.threshold)
            else: 
                self.func(self.threshold)
            self.helper_func()
            self.channels_func()
        else:
            self.func()
            self.channels_func()

        self.controller.show_frame("Loading")
        self.controller.pages["Loading"].start_work()

class Worker(QObject):
    finished = Signal()
    progress = Signal(int)
    result = Signal(str)

    def __init__(self, pipeline, save_path):
        super().__init__()
        self.pipeline = pipeline
        self.save_path = save_path

    @Slot()
    def do_work(self):
        print("Worker is running") 
        self.pipeline.align_time()
        self.pipeline.to_mat(self.save_path)
        self.result.emit("Work finished!")
        self.finished.emit()

class Loading(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.worker = None
        self.thread = None
        self.controller = controller
        
        self.layout = QVBoxLayout()
        container = QWidget()
        container_layout = QVBoxLayout()
        
        spin_layout = QVBoxLayout()
        spin_layout.setSpacing(0)
        spin_layout.setContentsMargins(0, 0, 0, 0)

        # Spinner (GIF) setup
        self.spinner = QSvgWidget("src/app/assets/830.svg")
        self.spinner.setFixedSize(128, 128)

        # Processing text label
        self.label = QLabel("Processing, please wait...")
        self.label.setAlignment(Qt.AlignCenter)

        # Start button
        next_button = QPushButton("Start")
        next_button.clicked.connect(lambda: self.controller.show_frame("File type"))

        # Spinner layout
        spin_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        spin_layout.addWidget(self.label)

        # Container layout
        container_layout.addLayout(spin_layout)
        container_layout.addWidget(next_button)
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
                border: 0px;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;}
            QLabel {
                color: black;
                border: 0px;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;}""")
        container.setFixedSize(700, 250)

        self.layout.addWidget(container, alignment=Qt.AlignCenter)
        self.setLayout(self.layout)
    
    @Slot()
    def start_work(self):
        self.worker = Worker(self.controller.obj, self.controller.dir_path)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.result.connect(self.display_result)
        self.thread.started.connect(self.worker.do_work)
        self.thread.start()

    @Slot(str)
    def display_result(self, message):
        self.spinner.hide()
        self.label.setText(message)

class MEAGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 960, 600)

        _id = QFontDatabase.addApplicationFont("C:/Users/Admin/UniBE/spike-sort/src/app/assets/fa-solid-900.ttf")

        self.obj = MEAPipeline()
        self.stack = QStackedWidget()
        self.flag = False

        self.pages = {
            "File type": ImportFile(self),
            "Save dir": savePath(self),
            "Contour detection": OptionSelect(self),
            'Loading': Loading(self)}
        
        for name, page in self.pages.items():
            self.stack.addWidget(page)
        
        title = QLabel("APP")
        title.setStyleSheet("font-size: 25px; font-weight: bold; padding-left: 15px;")

        howTo_button = QPushButton('Learn more')
        howTo_button.setIcon(QIcon('C:/Users/Admin/UniBE/spike-sort/src/app/assets/icons8-help-50.png'))
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

        self.progressbar = CustomProgressBar()
        self.progressbar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.progressbar.setFixedSize(550,55) 
        self.progressbar.labels = ["File type", "Save dir", "Contour detection", 'Results']

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
            self.stack.setCurrentWidget(page)
            index = list(self.pages.keys()).index(name)
            self.progressbar.value = index

stylesheet = """MEAGui {
        background-image: url("C:/Users/Admin/UniBE/spike-sort/src/app/assets/7178736_11911.jpg"); 
        background-repeat: no-repeat; 
        background-position: center;
    }"""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet)
    window = MEAGui()
    window.show()
    sys.exit(app.exec())