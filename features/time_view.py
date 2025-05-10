from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, 
                            QScrollArea, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import logging
import re

class TimeViewFeature:
    def __init__(self, parent, db, project_name):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.widget = QWidget()
        self.mqtt_tag = None
        self.window_size = 1.0
        self.data_rate = 4096.0
        self.buffer_size = int(self.data_rate * self.window_size)
        self.num_channels = 0
        self.time_view_buffers = []
        self.time_view_timestamps = deque(maxlen=self.buffer_size)
        self.timer = QTimer(self.widget)
        self.timer.timeout.connect(self.update_time_view_plot)
        self.plot_widgets = []  # List to hold separate PlotWidgets for each channel
        self.plots = []  # List to hold the plot items for each channel
        self.last_data_time = None
        self.is_saving = False
        self.frame_index = 0
        self.filename_counter = self.get_next_filename_counter()
        self.save_start_time = None
        self.save_end_time = None
        self.save_timer = QTimer(self.widget)
        self.save_timer.timeout.connect(self.update_save_duration)
        self.initUI()

    def get_widget(self):
        return self.widget

    def get_next_filename_counter(self):
        filenames = self.db.get_distinct_filenames(self.project_name)
        max_counter = 0
        for filename in filenames:
            match = re.match(r"data(\d+)", filename)
            if match:
                counter = int(match.group(1))
                max_counter = max(max_counter, counter)
        return max_counter + 1

    def initUI(self):
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        # Fixed control widget (outside scroll area)
        control_widget = QWidget()
        control_layout = QVBoxLayout()
        control_widget.setLayout(control_layout)
        control_widget.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px 20px;")

        # Header - Centered
        header = QLabel(f"TIME VIEW FOR {self.project_name.upper()}")
        header.setStyleSheet("color: white; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        self.header = header
        control_layout.addWidget(header, alignment=Qt.AlignCenter)

        # Tag selection row
        tag_layout = QHBoxLayout()
        tag_label = QLabel("Select Tag:")
        tag_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold; margin-right: 15px;")

        self.tag_combo = QComboBox()
        tags_data = list(self.db.tags_collection.find({"project_name": self.project_name}))
        if not tags_data:
            self.tag_combo.addItem("No Tags Available")
        else:
            for tag in tags_data:
                self.tag_combo.addItem(tag["tag_name"])
        self.tag_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                color: #212121;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: 500;
                min-width: 200px;
                max-width: 250px;
            }
            QComboBox:hover {
                border: 1px solid #42a5f5;
                background-color: #f5faff;
            }
            QComboBox:focus {
                border: 1px solid #1e88e5;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                width: 25px;
                border-left: 1px solid #e0e0e0;
                background-color: #e3f2fd;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 3px;
                selection-background-color: #e3f2fd;
                selection-color: #0d47a1;
                font-size: 14px;
                outline: 0;
            }
            QComboBox::item {
                padding: 4px 6px;
            }
            QComboBox::item:selected {
                background-color: #bbdefb;
                color: #0d47a1;
            }
        """)
        self.tag_combo.currentTextChanged.connect(self.setup_time_view_plot)

        tag_layout.addWidget(tag_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        tag_layout.addWidget(self.tag_combo, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        tag_layout.addStretch()
        tag_layout.setSpacing(0)
        control_layout.addLayout(tag_layout)

        # Save controls row
        save_layout = QHBoxLayout()
        filename_label = QLabel("Saving File:")
        filename_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold; margin-right: 15px;")

        self.filename_combo = QComboBox()
        self.filename_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                color: #212121;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: 500;
                min-width: 200px;
                max-width: 250px;
            }
            QComboBox:hover {
                border: 1px solid #42a5f5;
                background-color: #f5faff;
            }
            QComboBox:focus {
                border: 1px solid #1e88e5;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                width: 25px;
                border-left: 1px solid #e0e0e0;
                background-color: #e3f2fd;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 3px;
                selection-background-color: #e3f2fd;
                selection-color: #0d47a1;
                font-size: 14px;
                outline: 0;
            }
            QComboBox::item {
                padding: 4px 6px;
            }
            QComboBox::item:selected {
                background-color: #bbdefb;
                color: #0d47a1;
            }
        """)
        self.filename_combo.setEnabled(False)
        self.refresh_filenames()
        self.filename_combo.currentTextChanged.connect(self.open_data_table)

        self.start_save_button = QPushButton("Start Saving")
        self.start_save_button.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                margin-left: 10px;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: red;
                border: 1px solid #BDBDBD;
            }
        """)
        self.start_save_button.clicked.connect(self.start_saving)

        self.stop_save_button = QPushButton("Stop Saving")
        self.stop_save_button.setStyleSheet("""
            QPushButton {
                background-color: #e63946;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                margin-left: 10px;
            }
            QPushButton::pressed {
                background-color: red;
            }
        """)
        self.stop_save_button.clicked.connect(self.stop_saving)
        self.stop_save_button.setEnabled(False)

        self.timer_label = QLabel("Save Duration: 00:00:00")
        self.timer_label.setStyleSheet("color: white; font-size: 14px; font-weight: 500; margin-left: 15px;")

        save_layout.addWidget(filename_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        save_layout.addWidget(self.filename_combo, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        save_layout.addWidget(self.start_save_button, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        save_layout.addWidget(self.stop_save_button, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        save_layout.addWidget(self.timer_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        save_layout.addStretch()
        save_layout.setSpacing(0)
        control_layout.addLayout(save_layout)

        # Time info row
        time_info_layout = QHBoxLayout()
        self.start_time_label = QLabel("Start Time: N/A")
        self.start_time_label.setStyleSheet("color: white; font-size: 14px; font-weight: 500;")
        self.end_time_label = QLabel("End Time: N/A")
        self.end_time_label.setStyleSheet("color: white; font-size: 14px; font-weight: 500; margin-left: 20px;")
        self.latest_filename_label = QLabel(f"Saving File: data{self.filename_counter}")
        self.latest_filename_label.setStyleSheet("color: white; font-size: 14px; font-weight: 500; margin-left: 20px;")

        time_info_layout.addWidget(self.start_time_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        time_info_layout.addWidget(self.end_time_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        time_info_layout.addWidget(self.latest_filename_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        time_info_layout.addStretch()
        time_info_layout.setSpacing(0)
        control_layout.addLayout(time_info_layout)

        control_layout.setSpacing(15)
        control_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(control_widget)

        # Scrollable graph area
        self.graph_widget = QWidget()
        self.graph_layout = QVBoxLayout()
        self.graph_widget.setLayout(self.graph_layout)
        self.graph_widget.setStyleSheet("background-color: #2c3e50; border: 1px solid #ffffff; border-radius: 5px; padding: 8px;")

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.graph_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #2c3e50;
                border-radius: 5px;
            }
            QScrollBar:vertical {
                background: #ffffff;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #000000;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        scroll_area.setMinimumHeight(300)
        main_layout.addWidget(scroll_area)

        if tags_data:
            self.tag_combo.setCurrentIndex(0)
            self.setup_time_view_plot(self.tag_combo.currentText())

    def update_save_duration(self):
        if self.save_start_time:
            duration = datetime.now() - self.save_start_time
            seconds = duration.total_seconds()
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = int(seconds % 60)
            self.timer_label.setText(f"Save Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")
            current_time_str = datetime.now().strftime("%H:%M:%S")
            self.end_time_label.setText(f"End Time: {current_time_str}")

    def refresh_filenames(self):
        self.filename_combo.clear()
        filenames = self.db.get_distinct_filenames(self.project_name)
        for filename in filenames:
            self.filename_combo.addItem(filename)
        self.filename_combo.addItem(f"data{self.filename_counter} ")
        self.filename_combo.setCurrentText(f"data{self.filename_counter} ")
        if hasattr(self, 'latest_filename_label'):
            self.latest_filename_label.setText(f"Latest File: data{self.filename_counter}")

    def open_data_table(self, selected_filename):
        if "(Next)" in selected_filename:
            return
        
        if not self.db.timeview_collection.find_one({"filename": selected_filename, "project_name": self.project_name}):
            return

    def on_delete(self, deleted_filename):
        self.filename_counter = self.get_next_filename_counter()
        self.refresh_filenames()

    def start_saving(self):
        if not self.mqtt_tag or self.mqtt_tag == "No Tags Available":
            self.parent.append_to_console("Error: Please select a valid tag!")
            QMessageBox.warning(self.widget, "Error", "Please select a valid tag!")
            return
        
        filename = f"data{self.filename_counter}"
        self.is_saving = True
        self.frame_index = 0
        self.save_start_time = datetime.now()
        self.start_save_button.setEnabled(False)
        self.stop_save_button.setEnabled(True)
        self.save_timer.start(1000)
        self.parent.is_saving = True
        start_time_str = self.save_start_time.strftime("%H:%M:%S")
        self.start_time_label.setText(f"Start Time: {start_time_str}")
        self.end_time_label.setText(f"End Time: {start_time_str}")
        if hasattr(self, 'latest_filename_label'):
            self.latest_filename_label.setText(f"Latest File: {filename}")
        logging.info(f"Started saving data for {self.mqtt_tag} with filename {filename}")
        self.parent.append_to_console(f"Started saving data for {self.mqtt_tag} with filename {filename}")

    def stop_saving(self):
        if not self.is_saving:
            return
        
        self.is_saving = False
        self.start_save_button.setEnabled(True)
        self.stop_save_button.setEnabled(False)
        self.save_timer.stop()
        stop_time = datetime.now()
        self.save_end_time = stop_time
        self.parent.is_saving = False
        filename = f"data{self.filename_counter}"
        self.filename_counter += 1
        start_time_str = self.save_start_time.strftime("%H:%M:%S") if self.save_start_time else "N/A"
        stop_time_str = stop_time.strftime("%H:%M:%S")
        self.timer_label.setText("Save Duration: 00:00:00")
        self.start_time_label.setText(f"Start Time: {start_time_str}")
        self.end_time_label.setText(f"End Time: {stop_time_str}")
        if hasattr(self, 'latest_filename_label'):
            self.latest_filename_label.setText(f"Latest File: data{self.filename_counter}")
        logging.info(f"Stopped saving data for {self.mqtt_tag}")
        self.parent.append_to_console(f"Stopped saving data for {self.mqtt_tag}")
        self.save_start_time = None
        self.refresh_filenames()

    def setup_time_view_plot(self, tag_name):
        if not self.project_name or not tag_name or tag_name == "No Tags Available":
            logging.warning("No project or valid tag selected for Time View!")
            self.parent.append_to_console("No project or valid tag selected for Time View!")
            self.timer.stop()
            # Clear existing plot widgets
            for i in reversed(range(self.graph_layout.count())):
                self.graph_layout.itemAt(i).widget().setParent(None)
            self.plot_widgets = []
            self.plots = []
            return

        self.mqtt_tag = tag_name
        self.timer.stop()
        self.timer.setInterval(100)
        self.time_view_buffers = []
        self.time_view_timestamps.clear()
        self.last_data_time = None
        self.num_channels = 0
        self.plots = []
        self.plot_widgets = []
        self.is_saving = False
        self.start_save_button.setEnabled(True)
        self.stop_save_button.setEnabled(False)
        self.save_timer.stop()
        self.timer_label.setText("Save Duration: 00:00:00")
        self.timer_label.setStyleSheet("font-size: 14px; font-weight: 500; color: white; margin-left: 15px;")
        self.start_time_label.setText("Start Time: N/A")
        self.end_time_label.setText("End Time: N/A")
        if hasattr(self, 'latest_filename_label'):
            self.latest_filename_label.setText(f"Saving File: data{self.filename_counter}")
        self.frame_index = 0
        self.parent.is_saving = False

        # Clear existing plot widgets
        for i in reversed(range(self.graph_layout.count())):
            self.graph_layout.itemAt(i).widget().setParent(None)
        self.plot_widgets = []
        self.plots = []

        self.timer.start()
        logging.info(f"Initialized plot setup for tag {self.mqtt_tag}, buffer size: {self.buffer_size}")
        self.parent.append_to_console(f"Initialized plot setup for tag {self.mqtt_tag}")

    def initialize_plot(self, num_channels):
        if num_channels == self.num_channels and self.plots:
            return

        self.num_channels = num_channels
        self.buffer_size = int(self.data_rate * self.window_size)
        self.time_view_buffers = [deque(maxlen=self.buffer_size) for _ in range(num_channels)]
        self.time_view_timestamps = deque(maxlen=self.buffer_size)

        # Clear existing plot widgets
        for i in reversed(range(self.graph_layout.count())):
            self.graph_layout.itemAt(i).widget().setParent(None)
        self.plot_widgets = []
        self.plots = []

        # Create a separate PlotWidget for each channel
        colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        for i in range(num_channels):
            plot_widget = pg.PlotWidget()
            plot_widget.setBackground('w')
            plot_widget.showGrid(x=True, y=True, alpha=0.7)
            plot_widget.setXRange(0, self.window_size)
            plot_widget.setYRange(0, 65535)
            plot_widget.setLabel('bottom', 'Time (s)')
            plot_widget.setLabel('right', f'Channel {i+1}')
            plot_widget.getAxis('right').setStyle(tickTextOffset=10)
            plot_widget.getAxis('left').setStyle(showValues=False)
            plot = plot_widget.plot(pen=pg.mkPen(color=colors[i % len(colors)], width=1.5))
            self.plots.append(plot)
            self.plot_widgets.append(plot_widget)
            self.graph_layout.addWidget(plot_widget)

        self.graph_widget.setMinimumSize(1000, 300 * num_channels)
        logging.info(f"Initialized {num_channels} subplots for tag {self.mqtt_tag}")
        self.parent.append_to_console(f"Initialized {num_channels} subplots for tag {self.mqtt_tag}")

    def split_and_store_values(self, values, timestamp):
        try:
            if len(values) < 10:
                logging.warning(f"Insufficient data: received {len(values)} values, expected at least 10")
                self.parent.append_to_console(f"Insufficient data: received {len(values)} values")
                return

            frame_index = values[0] + (values[1] * 65535)
            number_of_channels = values[2]
            sampling_rate = values[3]
            sampling_size = values[4]
            message_frequency = values[5]
            slot6 = str(values[6])
            slot7 = str(values[7])
            slot8 = str(values[8])
            slot9 = str(values[9])

            plot_values = values[10:]
            if len(plot_values) % number_of_channels != 0:
                logging.warning(f"Unexpected number of plot values: {len(plot_values)}. Expected multiple of {number_of_channels}")
                self.parent.append_to_console(f"Unexpected number of plot values: {len(plot_values)}")
                return

            if number_of_channels != self.num_channels or not self.plots:
                self.initialize_plot(number_of_channels)

            num_samples = len(plot_values) // number_of_channels
            start_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if 'Z' in timestamp else datetime.fromisoformat(timestamp)
            timestamps = [start_time + timedelta(seconds=i / self.data_rate) for i in range(num_samples)]

            for i in range(0, len(plot_values), number_of_channels):
                sample_idx = i // number_of_channels
                try:
                    sample_values = [float(plot_values[i + j]) for j in range(number_of_channels)]
                    for j, buf in enumerate(self.time_view_buffers):
                        buf.append(sample_values[j])
                    self.time_view_timestamps.append(timestamps[sample_idx])
                except (ValueError, TypeError) as e:
                    logging.warning(f"Invalid sample at index {i}: {e}")
                    self.parent.append_to_console(f"Warning: Invalid sample data at index {i}")
                    continue

            if self.is_saving:
                filename = f"data{self.filename_counter}"
                message_data = {
                    "project_name": self.project_name,
                    "topic": self.mqtt_tag,
                    "filename": filename,
                    "frameIndex": frame_index,
                    "numberOfChannels": number_of_channels,
                    "samplingRate": sampling_rate,
                    "samplingSize": sampling_size,
                    "messageFrequency": message_frequency,
                    "slot6": slot6,
                    "slot7": slot7,
                    "slot8": slot8,
                    "slot9": slot9,
                    "message": plot_values,
                    "createdAt": timestamp
                }
                success, msg = self.db.save_timeview_message(self.project_name, message_data)
                if success:
                    self.frame_index += 1
                    self.header.setText(f"TIME VIEW FOR {self.project_name.upper()}")
                    logging.debug(f"Saved frame {self.frame_index - 1} for {self.mqtt_tag} to {filename}")
                    self.parent.append_to_console(f"Saved frame {self.frame_index - 1} to {filename}")
                else:
                    logging.error(f"Failed to save data: {msg}")
                    self.parent.append_to_console(f"Failed to save data: {msg}")
                    self.is_saving = False
                    self.start_save_button.setEnabled(True)
                    self.stop_save_button.setEnabled(False)
                    self.save_timer.stop()
                    self.start_time_label.setText("Start Time: N/A")
                    self.end_time_label.setText("End Time: N/A")
                    self.timer_label.setText("Save Duration: 00:00:00")
                    QMessageBox.critical(self.widget, "Error", f"Failed to save data: {msg}")

        except Exception as e:
            logging.error(f"Error processing values: {e}")
            self.parent.append_to_console(f"Error processing values: {e}")

    def adjust_buffer_size(self):
        new_buffer_size = int(self.data_rate * self.window_size)
        if new_buffer_size != self.buffer_size:
            self.buffer_size = new_buffer_size
            self.time_view_buffers = [deque(buf, maxlen=self.buffer_size) for buf in self.time_view_buffers]
            self.time_view_timestamps = deque(self.time_view_timestamps, maxlen=self.buffer_size)
            logging.info(f"Adjusted buffer size to {self.buffer_size}")
            self.parent.append_to_console(f"Adjusted buffer size to {self.buffer_size}")
            for widget in self.plot_widgets:
                widget.setXRange(0, self.window_size)

    def generate_y_ticks(self, values):
        if not values or not all(np.isfinite(v) for v in values):
            return np.arange(0, 65536, 10000)
        y_max = max(values)
        y_min = min(values)
        padding = (y_max - y_min) * 0.1 if y_max != y_min else 1000
        y_max += padding
        y_min -= padding
        step = (y_max - y_min) / 10
        step = np.ceil(step / 500) * 500
        ticks = np.arange(np.floor(y_min / step) * step, y_max + step, step)
        return ticks

    def update_time_view_plot(self):
        if not self.project_name or not self.mqtt_tag or not self.plots or not self.time_view_buffers:
            return

        current_buffer_size = len(self.time_view_buffers[0]) if self.time_view_buffers else 0
        if current_buffer_size == 0:
            return

        self.adjust_buffer_size()

        for i, (plot_widget, plot) in enumerate(zip(self.plot_widgets, self.plots)):
            window_values = list(self.time_view_buffers[i])
            window_timestamps = list(self.time_view_timestamps)

            if not window_values or not all(np.isfinite(v) for v in window_values):
                plot.setData([], [])
                plot_widget.setYRange(0, 65535)
                plot_widget.getAxis('right').setTicks([[(v, str(int(v))) for v in np.arange(0, 65536, 10000)]])
                continue

            time_points = np.linspace(0, self.window_size, len(window_values))
            plot.setData(time_points, window_values)
            y_ticks = self.generate_y_ticks(window_values)
            plot_widget.setYRange(min(window_values) - 1000, max(window_values) + 1000)
            plot_widget.getAxis('right').setTicks([[(v, str(int(v))) for v in y_ticks]])

            if window_timestamps:
                try:
                    start_time = window_timestamps[0]
                    end_time = window_timestamps[-1]
                    if isinstance(start_time, datetime) and isinstance(end_time, datetime):
                        tick_positions = np.linspace(0, self.window_size, 11)
                        time_labels = [
                            (start_time + timedelta(seconds=pos)).strftime('%H:%M:%S.%f')[:-3]
                            for pos in tick_positions
                        ]
                        axis = plot_widget.getAxis('bottom')
                        axis.setTicks([[(pos, label) for pos, label in zip(tick_positions, time_labels)]])
                except Exception as e:
                    logging.error(f"Error setting x-ticks for channel {i+1}: {e}")
                    self.parent.append_to_console(f"Error setting x-ticks: {str(e)}")

    def on_data_received(self, tag_name, values):
        if tag_name != self.mqtt_tag:
            return

        current_time = datetime.now()
        timestamp = current_time.isoformat()
        self.split_and_store_values(values, timestamp)