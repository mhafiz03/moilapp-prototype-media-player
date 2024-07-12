from src.plugin_interface import PluginInterface
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import QTimer
from .ui_main import Ui_Form
from src.models.plugins_model.resource_icon_and_pixmap import GetResourcesIcon
from src.models.shared_model import Model
import cv2
import os
import numpy as np

from multiprocessing import Pool, cpu_count


MOILDEV = None
ALPHA = 40
ZOOM = 3
CELL_WIDTH = None

def generate_map(beta_value):
    map_X, map_Y = MOILDEV.maps_anypoint_mode1(ALPHA, beta_value, ZOOM)
    
    h, w = map_X.shape
    scaling_factor = CELL_WIDTH / w
    new_w = int(w * scaling_factor)
    new_h = int(h * scaling_factor)
    
    x = cv2.resize(map_X, (new_w, new_h), interpolation=cv2.INTER_AREA)
    y = cv2.resize(map_Y, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    return x, y

class Controller(QWidget):
    def __init__(self, model : Model):
        super().__init__()
        self.ui = Ui_Form()
        self.model = model
        self.icon = GetResourcesIcon()
        self.ui.setupUi(self)
        self.connect_event()
        self.set_stylesheet()

        self.cap = None
        self.video = None
        self.image = None
        self.moildev = None
        self.source_media_active = None
        self.parameter_name_active = None
        self.cam_type_active = None
        self.source_type_active = None
        self.maps_x = None
        self.maps_y = None

        self.pos_frame = 0
        self.total_frame = 0

        self.width_image = self.round_to_nearest_100(self.ui.scrollArea.width()) - 20
        self.state = "fisheye"
        self.resizeEvent = self.resize_event_new_window
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame_signal)

        self.ui.label.setPixmap(self.icon.get_pixmap_vlc())
        self.ui.label.setScaledContents(True)

        self.beta_list = None
        self.grid_cols = 0

    def set_stylesheet(self):
        self.ui.frame_video_controller.setStyleSheet(self.model.style_frame_main())
        self.ui.btn_original_view.setIcon(self.icon.get_icon_fisheye_24px())
        self.ui.btn_2x3_view.setStyleSheet(self.model.style_pushbutton())
        self.ui.btn_2x4_view.setStyleSheet(self.model.style_pushbutton())
        self.ui.btn_3x5_view.setStyleSheet(self.model.style_pushbutton())
        self.ui.btn_4x6_view.setStyleSheet(self.model.style_pushbutton())
        self.ui.btn_zoom_in.setIcon(self.icon.get_icon_zoom_in())
        self.ui.btn_zoom_out.setIcon(self.icon.get_icon_zoom_out())
        self.ui.btn_play_pause.setIcon(self.icon.get_icon_play_video())
        self.ui.btn_rewind.setIcon(self.icon.get_icon_rewind_video())
        self.ui.btn_stop.setIcon(self.icon.get_icon_square())
        self.ui.btn_forward.setIcon(self.icon.get_icon_forward_video())
        self.ui.btn_change_source.setIcon(self.icon.get_icon_opened_folder())
        self.ui.btn_play_pause.setStyleSheet(self.model.style_pushbutton())
        self.ui.btn_rewind.setStyleSheet(self.model.style_pushbutton())
        self.ui.btn_play_pause.setStyleSheet(self.model.style_pushbutton_play_pause_video())
        self.ui.btn_stop.setStyleSheet(self.model.style_pushbutton())
        self.ui.btn_forward.setStyleSheet(self.model.style_pushbutton())
        self.ui.btn_change_source.setStyleSheet(self.model.style_pushbutton())


    def connect_event(self):
        self.ui.label.mousePressEvent = self.label_mouse_press_event
        self.ui.btn_zoom_in.clicked.connect(lambda: self.zoom_image("zoom_in"))
        self.ui.btn_zoom_out.clicked.connect(lambda: self.zoom_image("zoom_out"))
        self.ui.btn_original_view.clicked.connect(lambda: self.onclick_btn_state_view("fisheye"))
        self.ui.btn_2x3_view.clicked.connect(lambda: self.onclick_btn_state_view('2x3'))
        self.ui.btn_2x4_view.clicked.connect(lambda: self.onclick_btn_state_view('2x4'))
        self.ui.btn_3x5_view.clicked.connect(lambda: self.onclick_btn_state_view('3x5'))
        self.ui.btn_4x6_view.clicked.connect(lambda: self.onclick_btn_state_view('4x6'))
        self.ui.btn_change_source.clicked.connect(self.onclick_change_source)

        self.ui.btn_play_pause.clicked.connect(self.onclick_play_pause_video)
        self.ui.btn_stop.clicked.connect(self.stop_video)
        self.ui.btn_rewind.clicked.connect(self.rewind_video_5_second)
        self.ui.btn_forward.clicked.connect(self.forward_video_5_second)
        self.ui.slider_video_time.valueChanged.connect(self.set_value_change_slider)

    def resize_event_new_window(self, event):
        self.width_image = self.round_to_nearest_100(self.ui.scrollArea.width()) - 20
        self.show_image_result()

    def zoom_image(self, operation):
        if operation == "zoom_in":
            self.width_image = self.zoom_in(self.width_image)
        elif operation == "zoom_out":
            self.width_image = self.zoom_out(self.width_image)
        self.show_image_result()

    @classmethod
    def round_to_nearest_100(cls, num):
        return round(num / 20) * 20

    def onclick_btn_state_view(self, state):
        if self.image is not None:
            self.state = state
            if state != "fisheye":
                if state == "2x3":
                    self.set_grid_values(2, 3)
                elif state == "2x4":
                    self.set_grid_values(2, 4)
                elif state == "3x5":
                    self.set_grid_values(3, 5)
                elif state == "4x6":
                    self.set_grid_values(4, 6)
                self.create_grid()

            self.show_image_result()

    def label_mouse_press_event(self, event):
        if self.image is None:
            self.onclick_change_source()

    def onclick_change_source(self):
        if os.name == "nt":
            self.timer.stop()
            source_type, cam_type, source_media, parameter_name = self.model.select_media_source()
            if source_media is None:
                if self.source_media_active is not None:

                    self._handle_successful_media_selection(self.source_type_active,
                                                            self.cam_type_active,
                                                            self.source_media_active,
                                                            self.parameter_name_active)

                    self.show_message("Information!", "You have not selected any source; \n"
                                                      "it will continue with the previous source!!", timer=3000)
                else:
                    self.show_message("Information!", "You have not selected any source!", timer=3000)

            else:
                self.source_type_active = source_type
                self.cam_type_active = cam_type
                self.source_media_active = source_media
                self.parameter_name_active = parameter_name
                self._handle_successful_media_selection(self.source_type_active,
                                                        self.cam_type_active,
                                                        self.source_media_active,
                                                        self.parameter_name_active)

        else:
            source_type, cam_type, source_media, parameter_name = self.model.select_media_source()
            if source_media is None:
                if self.source_media_active is not None:
                    self._handle_successful_media_selection(self.source_type_active,
                                                            self.cam_type_active,
                                                            self.source_media_active,
                                                            self.parameter_name_active)
                    self.show_message("Information!", "You have not selected any source; \n"
                                                      "it will continue with the previous source!!", timer=3000)
                else:
                    self.show_message("Information!", "You have not selected any source!", timer=3000)

            else:
                self.source_type_active = source_type
                self.cam_type_active = cam_type
                self.source_media_active = source_media
                self.parameter_name_active = parameter_name
                self._handle_successful_media_selection(self.source_type_active,
                                                        self.cam_type_active,
                                                        self.source_media_active,
                                                        self.parameter_name_active)

    def _handle_successful_media_selection(self, source_type, cam_type, source_media, parameter_name):
        self.create_moildev(parameter_name)
        try:
            if source_type == "Open Camera":
                if cam_type in ["opencv_usb_cam", "opencv_ip_cam", "camera_url"]:
                    if os.name == 'nt':
                        if isinstance(source_media, int):
                            self.cap = cv2.VideoCapture(source_media, cv2.CAP_DSHOW)
                        else:
                            self.cap = cv2.VideoCapture(source_media)
                    else:
                        self.cap = cv2.VideoCapture(source_media)

                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.moildev.image_width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.moildev.image_height)
                    # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M', 'J', 'P', 'G'))
                    self.fps = 20
                    self.video = False
                    self.next_frame_signal()
                    print("Streaming Camera USB Camera")

                else:
                    print("streaming camera with others camera under developing!")

            elif source_type == "Image/Video":
                if source_media.endswith(('.mp4', '.MOV', '.avi')):
                    self.cap = cv2.VideoCapture(source_media)
                    self.pos_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                    self.total_frame = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    self.fps = self.cap.get(cv2.CAP_PROP_FPS)
                    self.video = True
                    self.next_frame_signal()
                    print("video source")

                elif source_media.endswith(('.jpeg', '.JPG', '.jpg', '.png', 'TIFF')):
                    print("image source")
                    self.cap = None
                    self.video = False
                    self.timer.stop()
                    self.image = cv2.imread(source_media)
                    self.show_image_result()

                else:
                    print("another source")

            self.ui.btn_play_pause.setChecked(True)
            self.onclick_play_pause_video()

        except Exception as e:
            print(f"Exception during select media: {e}")
            QMessageBox.warning(None, "Warning", "Cant load the history, have error in media source\n"
                                                 "Please check that your camera is on plug or \n"
                                                 "the file is exist!. you can select new media source.")
            print("some error in media_source")

    def create_moildev(self, parameter_name):
        global MOILDEV
        self.moildev = self.model.connect_to_moildev(parameter_name=parameter_name)
        MOILDEV = self.moildev

    def next_frame_signal(self):
        if self.cap is not None:
            success, self.image = self.cap.read()
            if self.video:
                if success:
                    self.pos_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                    self.show_image_result()
                    duration_sec = int(self.total_frame / self.fps)
                    total_minutes = duration_sec // 60
                    duration_sec %= 60
                    total_seconds = duration_sec
                    sec_pos = int(self.pos_frame / self.fps)
                    recent_minute = int(sec_pos // 60)
                    sec_pos %= 60
                    recent_sec = sec_pos
                    self.show_timer_video_info([total_minutes, total_seconds, recent_minute, recent_sec])

                else:
                    self.timer.stop()
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.total_frame - 1)
                    _, self.image = self.cap.read()
            else:
                self.show_timer_video_info([100, 0, 0, 0])

            self.set_slider_video_time_position()
            self.show_image_result()

    def onclick_play_pause_video(self):
        if self.cap is not None:
            if self.image is not None:
                if self.ui.btn_play_pause.isChecked():
                    self.ui.btn_play_pause.setIcon(self.icon.get_icon_pause_video())
                    self.timer.start(round(1000 / self.fps))
                else:
                    self.ui.btn_play_pause.setIcon(self.icon.get_icon_resume_video())
                    self.timer.stop()
        else:
            self.ui.btn_play_pause.setIcon(self.icon.get_icon_play_video())

    def set_slider_video_time_position(self):
        if self.cap is not None:
            if self.video:
                try:
                    dst_value = self.pos_frame * 100 / self.total_frame
                    self.ui.slider_video_time.blockSignals(True)
                    self.ui.slider_video_time.setValue(int(dst_value))
                    self.ui.slider_video_time.blockSignals(False)

                except Exception as e:
                    print(f"Exception during slider calculation: {e}")
                    self.ui.slider_video_time.setValue(int(100))

            else:
                self.ui.slider_video_time.setValue(int(100))

    def set_value_change_slider(self, value):
        if self.cap is not None:
            if self.video:
                dst_frame = self.total_frame * value / 100
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, dst_frame)
                self.next_frame_signal()

    def show_timer_video_info(self, list_timer):
        self.ui.label_current_time.setText("%02d:%02d" % (list_timer[2], list_timer[3]))
        self.ui.label_total_time.setText("%02d:%02d" % (list_timer[0], list_timer[1]))

    def stop_video(self):
        if self.cap is not None:
            if self.video:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.timer.stop()
                self.next_frame_signal()
                self.ui.btn_play_pause.setChecked(False)
                self.onclick_play_pause_video()

    def rewind_video_5_second(self):
        if self.cap is not None:
            if self.video:
                position = self.pos_frame - 5 * self.fps
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
                self.next_frame_signal()

    def forward_video_5_second(self):
        if self.cap is not None:
            if self.video:
                position = self.pos_frame + 5 * self.fps
                if position > self.total_frame:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.total_frame - 1)
                else:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
                self.next_frame_signal()

    def show_image_result(self):
        if self.image is not None:
            if self.state == "fisheye":
                self.model.show_image_to_label(self.ui.label, self.image, self.width_image)
            else:
                image = cv2.remap(self.image.copy(), self.maps_x, self.maps_y, interpolation=cv2.INTER_AREA)
                self.model.show_image_to_label(self.ui.label, image, self.width_image)

    def set_grid_values(self, grid_rows, grid_cols):
        global CELL_WIDTH
        CELL_WIDTH = self.width_image / grid_cols
        total_maps = grid_rows * grid_cols
        beta_increment = 360 / total_maps
        
        self.grid_cols = grid_cols
        self.beta_list = [i * beta_increment for i in range(total_maps)]
        self.total_maps = total_maps

    def create_grid(self):
        if self.moildev is None:
            return

        with Pool(processes=cpu_count()) as pool:
            results = pool.map(generate_map, self.beta_list)

        maps_x_list, maps_y_list = zip(*results)

        h_stacks_x = []
        h_stacks_y = []

        for i in range(0, self.total_maps, self.grid_cols):
            h_stacks_x.append(np.hstack(maps_x_list[i:i + self.grid_cols]))
            h_stacks_y.append(np.hstack(maps_y_list[i:i + self.grid_cols]))

        self.maps_x = np.vstack(h_stacks_x)
        self.maps_y = np.vstack(h_stacks_y)


    @classmethod
    def show_message(cls, title, message, timer=5000):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.show()
        QTimer.singleShot(timer, lambda: msg.done(0))

    @staticmethod
    def zoom_in(current_size):
        if current_size > 6000:
            pass
        else:
            current_size += 100
        return current_size

    @staticmethod
    def zoom_out(current_size):
        if current_size < 640:
            pass
        else:
            current_size -= 100
        return current_size


class MediaPlayer(PluginInterface):
    def __init__(self):
        super().__init__()
        self.widget = None
        self.description = "This is a plugins application"

    def set_plugin_widget(self, model):
        self.widget = Controller(model)
        return self.widget

    def set_icon_apps(self):
        return "icon.png"

    def change_stylesheet(self):
        self.widget.set_stylesheet()
