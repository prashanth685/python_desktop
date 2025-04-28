from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QTextEdit, 
                            QScrollArea, QPushButton, QMessageBox, QDialog, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import logging

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
        self.figure = plt.Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.last_data_time = None
        self.is_saving = False
        self.frame_index = 0
        self.filename_counter = self.get_next_filename_counter()
        self.save_start_time = None
        self.save_timer = QTimer(self.widget)
        self.save_timer.timeout.connect(self.update_save_duration)
        self.initUI()

    def get_next_filename_counter(self):
        filenames = self.db.timeview_collection.distinct("filename", {"project_name": self.project_name})
        max_counter = 0
        for filename in filenames:
            if filename.startswith("data") and filename[4:].isdigit():
                counter = int(filename[4:])
                max_counter = max(max_counter, counter)
        return max_counter + 1

    def initUI(self):
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        header = QLabel(f"TIME VIEW FOR {self.project_name.upper()}\n FRAME INDEX {self.frame_index}")
        header.setStyleSheet("color: white; font-size: 26px; font-weight: bold; padding: 8px;")
        layout.addWidget(header, alignment=Qt.AlignCenter)

        self.time_widget = QWidget()
        self.time_layout = QVBoxLayout()
        self.time_widget.setLayout(self.time_layout)
        self.time_widget.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px;")

        tag_layout = QHBoxLayout()
        tag_label = QLabel("Select Tag:")
        tag_label.setStyleSheet("color: white; font-size: 16px;")
        self.tag_combo = QComboBox()
        tags_data = list(self.db.tags_collection.find({"project_name": self.project_name}))
        if not tags_data:
            self.tag_combo.addItem("No Tags Available")
        else:
            for tag in tags_data:
                self.tag_combo.addItem(tag["tag_name"])
        self.tag_combo.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #1a73e8; padding: 15px")
        self.tag_combo.currentTextChanged.connect(self.setup_time_view_plot)

        tag_layout.addWidget(tag_label)
        tag_layout.addWidget(self.tag_combo)
        tag_layout.addStretch()
        self.time_layout.addLayout(tag_layout)

        save_layout = QHBoxLayout()
        filename_label = QLabel("Saved Files:")
        filename_label.setStyleSheet("color: white; font-size: 16px;")
        self.filename_combo = QComboBox()
        self.filename_combo.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #1a73e8; padding: 15px;")
        self.refresh_filenames()
        self.filename_combo.currentTextChanged.connect(self.open_data_table)

        self.start_save_button = QPushButton("Start Saving")
        self.start_save_button.setStyleSheet("background-color: #1a73e8; color: white; padding: 15px; border-radius: 5px;font-size:15px")
        self.start_save_button.clicked.connect(self.start_saving)
        
        self.stop_save_button = QPushButton("Stop Saving")
        self.stop_save_button.setStyleSheet("background-color: #e63946; color: white; padding: 15px; border-radius: 5px; font-size:15px")
        self.stop_save_button.clicked.connect(self.stop_saving)
        self.stop_save_button.setEnabled(False)

        self.timer_label = QLabel("Save Duration: 00:00:00")
        self.timer_label.setStyleSheet("color: white; font-size: 16px;")

        save_layout.addWidget(filename_label)
        save_layout.addWidget(self.filename_combo)
        save_layout.addWidget(self.start_save_button)
        save_layout.addWidget(self.stop_save_button)
        save_layout.addWidget(self.timer_label)
        save_layout.addStretch()
        self.time_layout.addLayout(save_layout)

        self.time_layout.addWidget(self.canvas)

        self.time_result = QTextEdit()
        self.time_result.setReadOnly(True)
        self.time_result.setStyleSheet("background-color: #34495e; color: white; border-radius: 5px; padding: 10px;")
        self.time_result.setMinimumHeight(50)
        self.time_layout.addWidget(self.time_result)
        self.time_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.time_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: black; border: none;color:black")
        scroll_area.setMaximumHeight(4000)
        layout.addWidget(scroll_area)

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

    def refresh_filenames(self):
        filenames = self.db.timeview_collection.distinct("filename", {"project_name": self.project_name})
        self.filename_combo.clear()
        for filename in sorted(filenames):
            self.filename_combo.addItem(filename)
        self.filename_combo.addItem(f"data{self.filename_counter} (Next)")
        self.filename_combo.setCurrentText(f"data{self.filename_counter} (Next)")

    def open_data_table(self, selected_filename):
        if "(Next)" in selected_filename:
            return
        
        if not self.db.timeview_collection.find_one({"filename": selected_filename, "project_name": self.project_name}):
            return

    def on_delete(self, deleted_filename):
        self.filename_counter = self.get_next_filename_counter()
        self.refresh_filenames()
        self.time_result.setText(f"Deleted data for {deleted_filename}")

    def start_saving(self):
        if not self.mqtt_tag or self.mqtt_tag == "No Tags Available":
            self.time_result.setText("Error: Please select a valid tag!")
            QMessageBox.warning(self.widget, "Error", "Please select a valid tag!")
            return
        
        filename = f"data{self.filename_counter}"
        self.is_saving = True
        self.frame_index = 0
        self.save_start_time = datetime.now()
        self.start_save_button.setEnabled(False)
        self.stop_save_button.setEnabled(True)
        self.save_timer.start(1000)  # Update timer every second
        self.parent.is_saving = True
        self.parent.play_action.setEnabled(False)
        self.parent.pause_action.setEnabled(True)
        start_time_str = self.save_start_time.strftime("%H:%M:%S")
        self.time_result.setText(f"Started saving data for {self.mqtt_tag} to {filename} at {start_time_str}")
        logging.info(f"Started saving data for {self.mqtt_tag} with filename {filename}")
        QMessageBox.information(self.widget, "Success", 
                              f"Started saving data for {self.mqtt_tag} to {filename} at {start_time_str}")

    def stop_saving(self):
        self.is_saving = False
        self.start_save_button.setEnabled(True)
        self.stop_save_button.setEnabled(False)
        self.save_timer.stop()
        stop_time = datetime.now()
        duration = stop_time - self.save_start_time
        self.parent.is_saving = False
        self.parent.play_action.setEnabled(True)
        self.parent.pause_action.setEnabled(False)
        filename = f"data{self.filename_counter}"
        self.filename_counter = self.get_next_filename_counter()
        start_time_str = self.save_start_time.strftime("%H:%M:%S")
        stop_time_str = stop_time.strftime("%H:%M:%S")
        self.timer_label.setText("Save Duration: 00:00:00")
        self.time_result.setText(f"Stopped saving data for {self.mqtt_tag} from {start_time_str} to {stop_time_str} (Duration: {str(duration).split('.')[0]})")
        logging.info(f"Stopped saving data for {self.mqtt_tag}")
        QMessageBox.information(self.widget, "Success", 
                              f"Stopped saving data for {self.mqtt_tag} from {start_time_str} to {stop_time_str}")
        self.save_start_time = None
        self.refresh_filenames()

    def setup_time_view_plot(self, tag_name):
        if not self.project_name or not tag_name or tag_name == "No Tags Available":
            logging.warning("No project or valid tag selected for Time View!")
            self.time_result.setText("No project or valid tag selected for Time View.")
            return

        self.mqtt_tag = tag_name
        self.timer.stop()
        self.timer.setInterval(100)
        self.time_view_buffers = []
        self.time_view_timestamps.clear()
        self.last_data_time = None
        self.buffer_size = int(self.data_rate * self.window_size)
        self.time_view_timestamps = deque(maxlen=self.buffer_size)
        self.is_saving = False
        self.start_save_button.setEnabled(True)
        self.stop_save_button.setEnabled(False)
        self.save_timer.stop()
        self.timer_label.setText("Save Duration: 00:00:00")
        self.timer_label.setStyleSheet("""
        font-size:20px;color:white;background-color:red
        """)
        self.frame_index = 0
        self.parent.is_saving = False
        self.parent.play_action.setEnabled(True)
        self.parent.pause_action.setEnabled(False)

        self.figure.clear()
        self.axes = []
        self.lines = []
        self.canvas.draw()
        self.timer.start()
        logging.info(f"Initialized plot setup for tag {self.mqtt_tag}, buffer size: {self.buffer_size}")

    def initialize_plot(self, num_channels):
        if num_channels == self.num_channels and self.axes:
            return

        self.num_channels = num_channels
        self.time_view_buffers = [deque(maxlen=self.buffer_size) for _ in range(num_channels)]
        self.figure.clear()
        self.axes = []
        self.lines = []

        for i in range(num_channels):
            ax = self.figure.add_subplot(num_channels, 1, i+1)
            line, = ax.plot([], [], f'C{i}-', linewidth=1.5)
            self.lines.append(line)
            self.axes.append(ax)
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.set_ylabel(f"Channel {i+1}", rotation=90, labelpad=10)
            ax.yaxis.set_label_position("right")
            ax.yaxis.tick_right()
            ax.set_xlabel("Time (HH:MM:SS.mmm)")
            ax.set_xlim(0, self.window_size)
            ax.set_ylim(15000, 50000)
            ax.set_xticks(np.linspace(0, self.window_size, 11))

        self.figure.subplots_adjust(left=0.05, right=0.85, top=0.95, bottom=0.15, hspace=0.4)
        self.canvas.setMinimumSize(1000, 800)
        self.time_widget.setMinimumSize(1000, 850)
        self.canvas.draw()
        logging.info(f"Initialized {num_channels} subplots for tag {self.mqtt_tag}")

    def split_and_store_values(self, values, timestamp):
        try:
            if len(values) < 10:
                logging.warning(f"Insufficient data: received {len(values)} values, expected at least 10.")
                self.time_result.setText(f"Warning: Received {len(values)} values, expected at least 10.")
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
                logging.warning(f"Unexpected number of plot values: {len(plot_values)}. Expected multiple of {number_of_channels}.")
                self.time_result.setText(f"Warning: Received {len(plot_values)} plot values, expected multiple of {number_of_channels}.")
                return

            if number_of_channels != self.num_channels or not self.axes:
                self.initialize_plot(number_of_channels)

            num_samples = len(plot_values) // number_of_channels
            start_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if 'Z' in timestamp else datetime.fromisoformat(timestamp)
            timestamps = [start_time + timedelta(seconds=i / self.data_rate) for i in range(num_samples)]

            for i in range(0, len(plot_values), number_of_channels):
                sample_idx = i // number_of_channels
                for j, buf in enumerate(self.time_view_buffers):
                    buf.append(plot_values[i + j])
                self.time_view_timestamps.append(timestamps[sample_idx])

            if self.is_saving:
                filename = f"data{self.filename_counter - 1}"  # Use current counter minus 1 as we're still saving to this file
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
                    logging.debug(f"Saved frame {self.frame_index - 1} for {self.mqtt_tag} to {filename}")
                    self.time_result.append(f"Saved frame {self.frame_index - 1} to {filename}")
                else:
                    logging.error(f"Failed to save data: {msg}")
                    self.time_result.setText(f"Error saving data: {msg}")

            logging.debug(f"Stored {num_samples} samples in buffer for {number_of_channels} channels")
        except Exception as e:
            logging.error(f"Error processing values: {e}")
            self.time_result.setText(f"Error processing data: {e}")

    def adjust_buffer_size(self):
        new_buffer_size = int(self.data_rate * self.window_size)
        if new_buffer_size != self.buffer_size:
            self.buffer_size = new_buffer_size
            self.time_view_buffers = [deque(buf, maxlen=self.buffer_size) for buf in self.time_view_buffers]
            self.time_view_timestamps = deque(self.time_view_timestamps, maxlen=self.buffer_size)
            logging.info(f"Adjusted buffer size to {self.buffer_size}")
            for ax in self.axes:
                ax.set_xlim(0, self.window_size)
                ax.set_xticks(np.linspace(0, self.window_size, 11))
            self.canvas.draw()

    def generate_y_ticks(self, values):
        if not values or not all(np.isfinite(v) for v in values):
            return np.arange(15000, 50001, 5000)
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
        if not self.project_name or not self.mqtt_tag:
            self.time_result.setText("No project or tag selected for Time View.")
            return

        if not self.axes or not self.time_view_buffers:
            return

        current_buffer_size = len(self.time_view_buffers[0])
        if current_buffer_size < 100:
            return

        self.adjust_buffer_size()

        for i, (ax, line) in enumerate(zip(self.axes, self.lines)):
            window_values = list(self.time_view_buffers[i])[-self.buffer_size:]
            window_timestamps = list(self.time_view_timestamps)[-self.buffer_size:]

            if not window_values or not all(np.isfinite(v) for v in window_values):
                self.time_result.setText(f"Invalid data for {self.mqtt_tag}. Buffer: {current_buffer_size}")
                ax.set_ylim(15000, 50000)
                ax.set_yticks(self.generate_y_ticks([]))
                line.set_data([], [])
                continue

            time_points = np.linspace(0, self.window_size, len(window_values))
            line.set_data(time_points, window_values)
            ax.set_ylim(min(window_values) - 1000, max(window_values) + 1000)
            ax.set_yticks(self.generate_y_ticks(window_values))

            if window_timestamps:
                try:
                    start_time = window_timestamps[0]
                    end_time = window_timestamps[-1]
                    if isinstance(start_time, datetime) and isinstance(end_time, datetime):
                        time_diff = (end_time - start_time).total_seconds()
                        tick_positions = np.linspace(0, self.window_size, 11)
                        time_labels = []
                        for pos in tick_positions:
                            fraction = pos / self.window_size
                            tick_time = start_time + timedelta(seconds=fraction * self.window_size)
                            milliseconds = tick_time.microsecond // 1000
                            time_labels.append(f"{tick_time.strftime('%H:%M:%S')}.{milliseconds:03d}\n{tick_time.strftime('%d-%m-%Y')}")
                        ax.set_xticks(tick_positions)
                        ax.set_xticklabels(time_labels, rotation=0, ha='left', fontsize=10)
                except Exception as e:
                    logging.error(f"Error setting x-ticks: {e}")
                    self.time_result.setText(f"Error setting x-ticks: {e}")

        self.canvas.draw()
        latest_values = [list(buf)[-1] if buf else None for buf in self.time_view_buffers]
        save_status = "Saving" if self.is_saving else "Not saving"

    def on_data_received(self, tag_name, values):
        if tag_name != self.mqtt_tag:
            return

        current_time = datetime.now()
        timestamp = current_time.isoformat()
        self.split_and_store_values(values, timestamp)
        logging.debug(f"Processed {len(values)} values for {tag_name}")

    def get_widget(self):
        return self.widget