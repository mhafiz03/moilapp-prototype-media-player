from src.plugin_interface import PluginInterface
from src.models.moilutils.components.select_media_source import CameraSource
from src.models.shared_model import Model
from PyQt6.QtWidgets import QWidget, QPushButton, QDialog, QStackedWidget, QLabel, QFileDialog, QMessageBox, QHBoxLayout, QVBoxLayout, QGridLayout, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData, QTimer
from PyQt6.QtGui import QDrag
import cv2
from .ffmpeg import CustomVideoCapture



class CustomStackedWidget(QWidget):
    def __init__(self, widgets, rows=1, columns=1):
        super().__init__()
        self.widget_lists = widgets
        self.rows = rows
        self.columns = columns
        self.initUI()

    def initUI(self):
        self.stackedPages = QStackedWidget()
        self.currentIndex = 0

        # Create navigation buttons
        self.prevButton = QPushButton("Previous")
        self.nextButton = QPushButton("Next")
        self.prevButton.clicked.connect(self.showPrevious)
        self.nextButton.clicked.connect(self.showNext)

        # Add widgets to the QStackedWidget
        self.updateStackedWidget()

        # Layout for navigation buttons
        navLayout = QHBoxLayout()
        navLayout.addWidget(self.prevButton)
        navLayout.addWidget(self.nextButton)

        # Main layout
        mainLayout = QVBoxLayout()
        mainLayout.addLayout(navLayout)
        mainLayout.addWidget(self.stackedPages)

        self.setLayout(mainLayout)
        self.updateButtons()

    def updateStackedWidget(self):
        # Clear existing widgets from the QStackedWidget
        while self.stackedPages.count() > 0:
            widget = self.stackedPages.widget(0)
            self.stackedPages.removeWidget(widget)
            widget.deleteLater()
        # Add widgets with the new grid size
        for i in range(0, len(self.widget_lists), self.rows * self.columns):
            page = QWidget()
            pageLayout = QGridLayout(page)
            for j in range(self.rows * self.columns):
                row, col = divmod(j, self.columns)
                if i + j < len(self.widget_lists):
                    pageLayout.addWidget(self.widget_lists[i + j], row, col)
                    self.widget_lists[i + j].cur_index = str(i + j)
            page.setLayout(pageLayout)
            self.stackedPages.addWidget(page)
        
        if self.rows * self.columns == len(self.widget_lists):
            self.nextButton.hide()
            self.prevButton.hide()
        else:
            self.nextButton.show()
            self.prevButton.show()

    def showPrevious(self):
        self.currentIndex -= 1
        if self.currentIndex < 0:
            self.currentIndex = self.stackedPages.count() - 1
        self.stackedPages.setCurrentIndex(self.currentIndex)
        self.updateButtons()

    def showNext(self):
        self.currentIndex += 1
        if self.currentIndex >= self.stackedPages.count():
            self.currentIndex = 0
        self.stackedPages.setCurrentIndex(self.currentIndex)
        self.updateButtons()

    def updateButtons(self):
        self.prevButton.setEnabled(self.stackedPages.count() > 1)
        self.nextButton.setEnabled(self.stackedPages.count() > 1)

    def setGridSize(self, rows, columns):
        self.rows = rows
        self.columns = columns
        self.updateStackedWidget()
        self.updateButtons()

      
class CustomWidget(QWidget):
    swap_signal = pyqtSignal(str, str)

    def __init__(self, enable_drag_drop=True):
        super().__init__()
        self.installEventFilter(self)
        self.enable_drag_drop = enable_drag_drop
        self.cur_index = '0'
        self.label = QLabel(self)
        self.label.setMinimumWidth(520)
        self.label.setMinimumHeight(320)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.v_layout = QVBoxLayout(self)
        self.v_layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(self.v_layout)

        self.setMinimumSize(QSize(340, 260))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setAcceptDrops(True)
    
    def get_width(self) -> int:
        if self.scrollArea:
            w = self.scrollArea.width()
            if w is not None: return w

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.enable_drag_drop:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.cur_index)
            drag.setMimeData(mime_data)

            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint() - self.rect().topLeft())

            self.hide()
            drag.exec(Qt.DropAction.MoveAction)
            self.show()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            sender = event.mimeData().text()
            receiver = self.cur_index
            self.swap_signal.emit(sender, receiver)


class CustomCameraSource(CameraSource):
    def open_media_path(self):
        self.__file_path, _ = QFileDialog.getOpenFileName(None, "Load Media", "../", "Files format (*.jpeg *.jpg *.png *.avi *.mp4 *.webm *.mkv)", options=QFileDialog.Option.DontUseNativeDialog)
        if self.__file_path.endswith(('.png', '.jpg', '.jpeg')):
            parameter = self.read_camera_type(self.__file_path)
            self.index = self.comboBox_parameters.findText(parameter)
            if self.index != -1:
                self.comboBox_parameters.setCurrentIndex(self.index)
                self.comboBox_parameters.setStyleSheet("color:rgb(100,100,100);")
                self.comboBox_parameters.setEnabled(False)
            else:
                QMessageBox.information(None, "Information", 'Camera Parameter Not Available on the list \n' 'You can open the parameter form and \n' 'synchronize or select the available list!!')
        else:
            self.comboBox_parameters.setStyleSheet("color:rgb(255,255,255);")
            self.comboBox_parameters.setEnabled(True)
        self.media_path.setText(self.__file_path)


class CustomModel(Model):
    cap = None
    video = None
    image = None

    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame_signal)

    def set_media_source(self, source_type, cam_type, media_source, params_name):
        if source_type == "Streaming Camera":
            self.cap = self.model.moil_camera(cam_type=cam_type, cam_id=media_source)
            self.video = False
        elif source_type == "Image/Video":
            if media_source.endswith(('.mp4', '.MOV', '.avi')):
                self.cap = cv2.VideoCapture(media_source)
                _, self.image = self.cap.read()
                self.video = True
            elif media_source.endswith(('.jpeg', '.jpg', '.png')):
                self.cap = None
                self.video = False
                self.image = cv2.imread(media_source)
            elif media_source.endswith(('.webm')):
                self.cap = CustomVideoCapture(media_source, 5)
                self.video = True

    def set_labels(self, label_list):
        self.labels = label_list
        # HARD CODED
        width = 1944
        height = 972
        self.cell_width = width // 3
        self.cell_height = height // 2

    def next_frame_signal(self):
        if self.video:
            success, self.image = self.cap.read()
            if not success: 
                self.timer.stop()
                return
        elif self.cap:
            self.image = self.cap.frame()
        self.show_image()

    def show_image(self):
        for row in range(2):
            for col in range(3):
                x_start = col * self.cell_width
                x_end = x_start + self.cell_width
                y_start = row * self.cell_height
                y_end = y_start + self.cell_height
                index = row * 3 + col 
                self.show_image_to_label(self.labels[index], self.image[y_start:y_end, x_start:x_end], 520)

    def stop(self):
        self.timer.stop()
        if self.video:
            self.cap.release()
        self.cap = None
        self.image = None
        for i, label in enumerate(self.labels):
            label.setText(' ')

    @staticmethod
    def select_media_source():
        open_cam_source = QDialog()
        source_cam = CustomCameraSource(open_cam_source)
        open_cam_source.exec()
        media_source = source_cam.camera_source
        params_name = source_cam.parameter_selected
        cam_type = source_cam.cam_type
        source_type = source_cam.comboBox_camera_sources.currentText()
        return source_type, cam_type, media_source, params_name


class Controller(QWidget):
    def __init__(self, _):
        super().__init__()
        self.model = CustomModel()

        widgets = [CustomWidget(enable_drag_drop=True) for i in range(6)]
        self.stacked_widgets = CustomStackedWidget(widgets, 2, 3)
        self.v_layout = QVBoxLayout(self)
        self.btn_layout = QHBoxLayout(self)
        
        self.media_btn = QPushButton('Select Media', self)
        self.play_pause_btn = QPushButton('Play/Pause', self)
        self.close_btn = QPushButton('Close', self)
        self.btn_layout.addWidget(self.media_btn)
        self.btn_layout.addWidget(self.play_pause_btn)
        self.btn_layout.addWidget(self.close_btn)
        
        self.v_layout.addLayout(self.btn_layout)
        self.v_layout.addWidget(self.stacked_widgets)
        self.setLayout(self.v_layout)
        
        [w.swap_signal.connect(self.handle_swapping) for w in self.stacked_widgets.widget_lists]

        self.set_stylesheet()
        self.connect_buttons()

    def set_stylesheet(self):    
        [btn.setStyleSheet(self.model.style_pushbutton()) for btn in self.findChildren(QPushButton)]
        [lbl.setStyleSheet(self.model.style_label()) for lbl in self.findChildren(QLabel)]
    
    def connect_buttons(self):
        self.media_btn.clicked.connect(self.media_btn_clicked)
        self.play_pause_btn.clicked.connect(self.play_pause_btn_clicked)
        self.close_btn.clicked.connect(self.close_btn_clicked)

    def media_btn_clicked(self):
        source_type, cam_type, media_source, params_name = self.model.select_media_source()
        if media_source is not None:
            self.model.set_media_source(source_type, cam_type, media_source, params_name)
            self.model.set_labels([w.label for w in self.stacked_widgets.widget_lists])

    def play_pause_btn_clicked(self):
        self.model.timer.stop() if self.model.timer.isActive() else self.model.timer.start()

    def close_btn_clicked(self):
        self.model.stop()
    
    def handle_swapping(self, sender, receiver):
        sender = int(sender)
        receiver = int(receiver)
        self.stacked_widgets.widget_lists[sender], self.stacked_widgets.widget_lists[receiver] = self.stacked_widgets.widget_lists[receiver], self.stacked_widgets.widget_lists[sender]
        self.stacked_widgets.updateStackedWidget()
        




class PrototypeMediaPlayer(PluginInterface):
    def __init__(self):
        super().__init__()
        self.widget = None
        self.description = "Moilapp Plugin: Surveillance monitoring area using Fisheye Camera for a wide 360deg view"

    def set_plugin_widget(self, model):
        self.widget = Controller(model)
        return self.widget

    def set_icon_apps(self): 
        return "icon.png"
    
    def change_stylesheet(self): 
        self.widget.set_stylesheet()
