from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton, QScrollArea, QDateTimeEdit, QGridLayout)
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
from PyQt5.QtCore import Qt, QDateTime, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
from datetime import datetime, timedelta
import logging
import re

class QRangeSlider(QWidget):
    """Custom dual slider widget for selecting a time range."""
    valueChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(30)
        self.setMinimumWidth(300)
        self.min_value = 0
        self.max_value = 1000
        self.left_value = 0
        self.right_value = 1000
        self.dragging = None
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QWidget {
                background-color: #34495e;
            }
        """)

    def setRange(self, min_val, max_val):
        self.min_value = min_val
        self.max_value = max_val
        self.left_value = max(self.min_value, min(self.left_value, self.max_value))
        self.right_value = max(self.min_value, min(self.right_value, self.max_value))
        self.update()

    def setValues(self, left, right):
        self.left_value = max(self.min_value, min(left, self.max_value))
        self.right_value = max(self.min_value, min(right, self.max_value))
        self.update()
        self.valueChanged.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        groove_rect = QRect(int(10), int(10), int(self.width() - 20), int(8))
        painter.setPen(QPen(QColor("#1a73e8")))
        painter.setBrush(QColor("#34495e"))
        painter.drawRoundedRect(groove_rect, 4, 4)

        left_pos = int(self._value_to_pos(self.left_value))
        right_pos = int(self._value_to_pos(self.right_value))
        selected_rect = QRect(left_pos, int(10), int(right_pos - left_pos), int(8))
        painter.setBrush(QColor("#90caf9"))
        painter.drawRoundedRect(selected_rect, 4, 4)

        painter.setPen(QPen(QColor("#1a73e8")))
        painter.setBrush(QColor("#42a5f5" if self.dragging == 'left' else "#1a73e8"))
        painter.drawEllipse(left_pos - 9, 6, 18, 18)
        painter.setBrush(QColor("#42a5f5" if self.dragging == 'right' else "#1a73e8"))
        painter.drawEllipse(right_pos - 9, 6, 18, 18)

    def _value_to_pos(self, value):
        if self.max_value == self.min_value:
            return 10
        return 10 + (self.width() - 20) * (value - self.min_value) / (self.max_value - self.min_value)

    def _pos_to_value(self, pos):
        if self.width() <= 20:
            return self.min_value
        value = self.min_value + (pos - 10) / (self.width() - 20) * (self.max_value - self.min_value)
        return max(self.min_value, min(self.max_value, value))

    def mousePressEvent(self, event):
        pos = event.pos().x()
        left_pos = self._value_to_pos(self.left_value)
        right_pos = self._value_to_pos(self.right_value)
        if abs(pos - left_pos) < abs(pos - right_pos) and abs(pos - left_pos) < 10:
            self.dragging = 'left'
        elif abs(pos - right_pos) <= abs(pos - left_pos) and abs(pos - right_pos) < 10:
            self.dragging = 'right'
        self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            pos = event.pos().x()
            value = self._pos_to_value(pos)
            if self.dragging == 'left':
                self.left_value = max(self.min_value, min(value, self.max_value))
            elif self.dragging == 'right':
                self.right_value = max(self.min_value, min(value, self.max_value))
            self.update()
            self.valueChanged.emit()

    def mouseReleaseEvent(self, event):
        self.dragging = None
        self.update()

    def getValues(self):
        return self.left_value, self.right_value

class TimeReportFeature:
    def __init__(self, parent, db, project_name):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.widget = QWidget(self.parent)
        self.figure = plt.Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.file_start_time = None
        self.file_end_time = None
        self.initUI()
    def animate_button_press(self):
        animation = QPropertyAnimation(self.ok_button, b"styleSheet")
        animation.setDuration(200)
        animation.setStartValue("background-color: #1a73e8;")
        animation.setEndValue("background-color: #155ab6;")
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()

    def initUI(self):
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        header = QLabel(f"TIME REPORT FOR {self.project_name.upper()}")
        header.setStyleSheet("color: white; font-size: 26px; font-weight: bold; padding: 8px;")
        layout.addWidget(header, alignment=Qt.AlignCenter)

        self.report_widget = QWidget()
        self.report_layout = QVBoxLayout()
        self.report_widget.setLayout(self.report_layout)
        self.report_widget.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px;")

        file_layout = QHBoxLayout()
        file_label = QLabel("Select Saved File:")
        file_label.setStyleSheet("color: white; font-size: 16px;font:bold")
        self.file_combo = QComboBox()
        self.file_combo.setStyleSheet("""
            QComboBox {
                background-color: #fdfdfd;
                color: #212121;
                border: 2px solid #90caf9;
                border-radius: 8px;
                padding: 10px 40px 10px 14px;
                font-size: 16px;
                font-weight: 600;
                min-width: 220px;
                box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.05);
            }
            QComboBox:hover {
                border: 2px solid #42a5f5;
                background-color: #f5faff;
            }
            QComboBox:focus {
                border: 2px solid #1e88e5;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 36px;
                border-left: 1px solid #e0e0e0;
                background-color: #e3f2fd;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 5px;
                selection-background-color: #e3f2fd;
                selection-color: #0d47a1;
                font-size: 15px;
                outline: 0;
            }
            QComboBox::item {
                padding: 10px 8px;
                border: none;
            }
            QComboBox::item:selected {
                background-color: #bbdefb;
                color: #0d47a1;
            }""")
        self.file_combo.currentTextChanged.connect(self.update_time_labels)

        self.ok_button = QPushButton("OK")
        self.ok_button.setStyleSheet("""
    QPushButton {
        background-color: #1a73e8;
        color: white;
        padding: 15px;
        font-size: 15px;
        width: 100px;
        border-radius: 50%;
        font-weight: bold;
    }
    QPushButton:pressed {
        background-color: darkgreen;  /* darker blue when pressed */
    }
""")

        self.ok_button.clicked.connect(self.plot_data)
        self.ok_button.setEnabled(False)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_combo)
        file_layout.addWidget(self.ok_button)
        file_layout.addStretch()
        self.report_layout.addLayout(file_layout)

        time_range_layout = QHBoxLayout()
        start_time_label = QLabel("Select Start Time:")
        start_time_label.setStyleSheet("color: white; font-size: 14px;font:bold")
        self.start_time_edit = QDateTimeEdit()
        self.start_time_edit.setStyleSheet("background-color: #34495e; color: white; border: 2px solid white; padding: 15px;font:bold;width:200px")
        self.start_time_edit.setDisplayFormat("HH:mm:ss")
        # self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.dateTimeChanged.connect(self.validate_time_range)

        end_time_label = QLabel("Select End Time:")
        end_time_label.setStyleSheet("color: white; font-size: 14px;font:bold")
        self.end_time_edit = QDateTimeEdit()
        self.end_time_edit.setStyleSheet("background-color: #34495e; color: white; border: 2px solid white; padding: 15px;font:bold;width:200px")
        self.end_time_edit.setDisplayFormat("HH:mm:ss")
        # self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.dateTimeChanged.connect(self.validate_time_range)

        time_range_layout.addWidget(start_time_label)
        time_range_layout.addWidget(self.start_time_edit)
        time_range_layout.addWidget(end_time_label)
        time_range_layout.addWidget(self.end_time_edit)
        time_range_layout.addStretch()
        self.report_layout.addLayout(time_range_layout)

        slider_layout = QGridLayout()
        slider_label = QLabel("Drag Time Range:")
        slider_label.setStyleSheet("color: white; font-size: 14px;font:bold")
        slider_label.setFixedWidth(150)
        self.time_slider = QRangeSlider(self.widget)
        self.time_slider.valueChanged.connect(self.update_time_from_slider)
        slider_layout.addWidget(slider_label, 0, 0, 1, 1, Qt.AlignLeft | Qt.AlignVCenter)
        slider_layout.addWidget(self.time_slider, 0, 1, 1, 1)
        slider_layout.setColumnStretch(1, 1)
        self.report_layout.addLayout(slider_layout)

        time_info_layout = QHBoxLayout()
        self.start_time_label = QLabel("File Start Time: N/A")
        self.start_time_label.setStyleSheet("color: white; font-size: 14px;font:bold")
        self.stop_time_label = QLabel("File Stop Time: N/A")
        self.stop_time_label.setStyleSheet("color: white; font-size: 14px;font:bold")
        time_info_layout.addWidget(self.start_time_label)
        time_info_layout.addWidget(self.stop_time_label)
        time_info_layout.addStretch()
        self.report_layout.addLayout(time_info_layout)

        self.report_layout.addWidget(self.canvas)
        self.report_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.report_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border-radius: 8px;
                padding: 5px;
            }

            QScrollBar:vertical {
                background: white;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical {
                background: black;
                border-radius: 5px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        layout.addWidget(scroll_area)

        self.refresh_filenames()

    def refresh_filenames(self):
        self.file_combo.clear()
        try:
            filenames = self.db.get_distinct_filenames(self.project_name)
            if not filenames:
                self.file_combo.addItem("No Files Available")
                self.parent.append_to_console("No saved files found for this project.")
                self.start_time_label.setText("File Start Time: N/A")
                self.stop_time_label.setText("File Stop Time: N/A")
                self.start_time_edit.setEnabled(False)
                self.end_time_edit.setEnabled(False)
                self.time_slider.setEnabled(False)
                self.ok_button.setEnabled(False)
                self.figure.clear()
                self.canvas.draw()
            else:
                for filename in filenames:
                    self.file_combo.addItem(filename)
                self.start_time_edit.setEnabled(True)
                self.end_time_edit.setEnabled(True)
                self.time_slider.setEnabled(True)
                self.ok_button.setEnabled(True)
                self.update_time_labels(self.file_combo.currentText())
        except Exception as e:
            logging.error(f"Error refreshing filenames: {e}")
            self.file_combo.addItem("Error Loading Files")
            self.parent.append_to_console(f"Error loading saved files: {str(e)}")
            self.start_time_label.setText("File Start Time: N/A")
            self.stop_time_label.setText("File Stop Time: N/A")
            self.start_time_edit.setEnabled(False)
            self.end_time_edit.setEnabled(False)
            self.time_slider.setEnabled(False)
            self.ok_button.setEnabled(False)
            self.figure.clear()
            self.canvas.draw()

    def update_time_labels(self, filename):
        if not filename or filename in ["No Files Available", "Error Loading Files"]:
            self.start_time_label.setText("File Start Time: N/A")
            self.stop_time_label.setText("File Stop Time: N/A")
            self.start_time_edit.setEnabled(False)
            self.end_time_edit.setEnabled(False)
            self.time_slider.setEnabled(False)
            self.ok_button.setEnabled(False)
            self.file_start_time = None
            self.file_end_time = None
            return

        try:
            data = list(self.db.timeview_collection.find(
                {"filename": filename, "project_name": self.project_name}
            ).sort("frameIndex", 1))
            
            if not data:
                self.start_time_label.setText("File Start Time: N/A")
                self.stop_time_label.setText("File Stop Time: N/A")
                self.start_time_edit.setEnabled(False)
                self.end_time_edit.setEnabled(False)
                self.time_slider.setEnabled(False)
                self.ok_button.setEnabled(False)
                self.parent.append_to_console(f"No data found for file: {filename}")
                self.file_start_time = None
                self.file_end_time = None
                return

            timestamps = []
            for item in data:
                created_at = item.get("createdAt")
                try:
                    timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if 'Z' in created_at else datetime.fromisoformat(created_at)
                    timestamps.append(timestamp)
                except Exception as e:
                    logging.warning(f"Invalid timestamp in {filename}: {e}")
                    self.parent.append_to_console(f"Invalid timestamp in {filename}: {e}")
                    continue

            if timestamps:
                self.file_start_time = min(timestamps)
                self.file_end_time = max(timestamps)
                self.start_time_label.setText(f"File Start Time: {self.file_start_time.strftime('%H:%M:%S')}")
                self.stop_time_label.setText(f"File Stop Time: {self.file_end_time.strftime('%H:%M:%S')}")
                self.start_time_edit.setEnabled(True)
                self.end_time_edit.setEnabled(True)
                self.time_slider.setEnabled(True)
                self.ok_button.setEnabled(True)
                self.start_time_edit.setDateTime(QDateTime(self.file_start_time))
                self.end_time_edit.setDateTime(QDateTime(self.file_end_time))
                self.time_slider.setRange(0, 1000)
                self.time_slider.setValues(0, 1000)
            else:
                self.start_time_label.setText("File Start Time: N/A")
                self.stop_time_label.setText("File Stop Time: N/A")
                self.start_time_edit.setEnabled(False)
                self.end_time_edit.setEnabled(False)
                self.time_slider.setEnabled(False)
                self.ok_button.setEnabled(False)
                self.file_start_time = None
                self.file_end_time = None
        except Exception as e:
            logging.error(f"Error updating time labels for {filename}: {e}")
            self.start_time_label.setText("File Start Time: N/A")
            self.stop_time_label.setText("File Stop Time: N/A")
            self.start_time_edit.setEnabled(False)
            self.end_time_edit.setEnabled(False)
            self.time_slider.setEnabled(False)
            self.ok_button.setEnabled(False)
            self.parent.append_to_console(f"Error loading time data for {filename}: {str(e)}")
            self.file_start_time = None
            self.file_end_time = None

    def update_time_from_slider(self):
        if not self.file_start_time or not self.file_end_time:
            return

        total_duration = (self.file_end_time - self.file_start_time).total_seconds()
        if total_duration <= 0:
            return

        left_pos, right_pos = self.time_slider.getValues()
        if left_pos > right_pos:
            left_pos, right_pos = right_pos, left_pos
            self.time_slider.setValues(left_pos, right_pos)

        left_fraction = left_pos / 1000.0
        right_fraction = right_pos / 1000.0

        start_seconds = left_fraction * total_duration
        end_seconds = right_fraction * total_duration
        start_time = self.file_start_time + timedelta(seconds=start_seconds)
        end_time = self.file_start_time + timedelta(seconds=end_seconds)

        self.start_time_edit.blockSignals(True)
        self.end_time_edit.blockSignals(True)
        self.start_time_edit.setDateTime(QDateTime(start_time))
        self.end_time_edit.setDateTime(QDateTime(end_time))
        self.start_time_edit.blockSignals(False)
        self.end_time_edit.blockSignals(False)

        self.validate_time_range()

    def validate_time_range(self):
        start_time = self.start_time_edit.dateTime().toPyDateTime()
        end_time = self.end_time_edit.dateTime().toPyDateTime()

        if start_time >= end_time:
            self.ok_button.setEnabled(False)
            self.parent.append_to_console("Error: Start time must be before end time.")
        else:
            self.ok_button.setEnabled(True)
            if self.file_start_time and self.file_end_time:
                total_duration = (self.file_end_time - self.file_start_time).total_seconds()
                if total_duration > 0:
                    start_offset = (start_time - self.file_start_time).total_seconds()
                    end_offset = (end_time - self.file_start_time).total_seconds()
                    left_pos = (start_offset / total_duration) * 1000
                    right_pos = (end_offset / total_duration) * 1000
                    self.time_slider.blockSignals(True)
                    self.time_slider.setValues(left_pos, right_pos)
                    self.time_slider.blockSignals(False)

    def plot_data(self):
        filename = self.file_combo.currentText()
        if not filename or filename in ["No Files Available", "Error Loading Files"]:
            self.parent.append_to_console("No valid file selected to plot.")
            self.figure.clear()
            self.canvas.draw()
            return

        start_time = self.start_time_edit.dateTime().toPyDateTime()
        end_time = self.end_time_edit.dateTime().toPyDateTime()
        if start_time >= end_time:
            self.parent.append_to_console("Error: Start time must be before end time.")
            self.figure.clear()
            self.canvas.draw()
            return

        self.figure.clear()
        try:
            data = list(self.db.timeview_collection.find(
                {"filename": filename, "project_name": self.project_name}
            ).sort("frameIndex", 1))
            
            if not data:
                self.parent.append_to_console(f"No data found for file: {filename}")
                self.figure.clear()
                self.canvas.draw()
                return

            num_channels = data[0].get("numberOfChannels", 1)
            data_rate = data[0].get("samplingRate", 4096.0)
            if not isinstance(num_channels, int) or num_channels < 1:
                self.parent.append_to_console(f"Invalid number of channels ({num_channels}) for file: {filename}")
                self.figure.clear()
                self.canvas.draw()
                return

            channel_values = [[] for _ in range(num_channels)]
            time_points = []
            timestamps = []
            current_time_offset = 0

            for item in data:
                values = item.get("message", [])
                if not values:
                    logging.warning(f"Empty message in frame {item.get('frameIndex')} for {filename}")
                    self.parent.append_to_console(f"Warning: Empty message in frame {item.get('frameIndex')} for {filename}")
                    continue
                
                try:
                    created_at = item.get("createdAt")
                    if not created_at:
                        raise ValueError("Missing createdAt field")
                    timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if 'Z' in created_at else datetime.fromisoformat(created_at)
                except Exception as e:
                    logging.error(f"Invalid createdAt timestamp in frame {item.get('frameIndex')}: {e}")
                    self.parent.append_to_console(f"Error: Invalid timestamp in frame {item.get('frameIndex')} for {filename}")
                    continue

                if timestamp < start_time or timestamp > end_time:
                    continue

                if len(values) % num_channels != 0:
                    logging.warning(f"Invalid data in frame {item.get('frameIndex')}: {len(values)} values not divisible by {num_channels} channels")
                    self.parent.append_to_console(f"Warning: Invalid data in frame {item.get('frameIndex')}: {len(values)} values not divisible by {num_channels} channels")
                    continue

                num_samples = len(values) // num_channels
                for sample_idx in range(num_samples):
                    sample_time = timestamp + timedelta(seconds=sample_idx / data_rate)
                    if start_time <= sample_time <= end_time:
                        time_points.append(current_time_offset + sample_idx / data_rate)
                        timestamps.append(sample_time)
                        for channel in range(num_channels):
                            value_idx = sample_idx * num_channels + channel
                            try:
                                channel_values[channel].append(float(values[value_idx]))
                            except (ValueError, TypeError) as e:
                                logging.warning(f"Invalid value at frame {item.get('frameIndex')}, sample {sample_idx}, channel {channel}: {e}")
                                self.parent.append_to_console(f"Warning: Invalid value at frame {item.get('frameIndex')}, channel {channel + 1}")
                current_time_offset += num_samples / data_rate

            if not time_points or not any(channel_values):
                self.parent.append_to_console(f"No data found in the selected time range for file: {filename}")
                self.figure.clear()
                self.canvas.draw()
                return

            axes = []
            lines = []
            window_size = max(time_points) if time_points else 1.0

            def time_formatter(x, pos):
                actual_time = start_time + timedelta(seconds=x)
                return actual_time.strftime('%H:%M:%S:%f')[:-3] + '\n' + actual_time.strftime('%d-%m-%Y')

            for channel in range(num_channels):
                ax = self.figure.add_subplot(num_channels, 1, channel + 1)
                if channel_values[channel]:
                    line, = ax.plot(time_points, channel_values[channel], f'C{channel}-', linewidth=1.5)
                    lines.append(line)
                    ax.grid(True, linestyle='--', alpha=0.7)
                    ax.set_ylabel(f"Channel {channel + 1}", rotation=0, labelpad=40, fontweight='bold')
                    ax.yaxis.set_label_position("right")
                    ax.yaxis.tick_right()
                    ax.set_xlim(0, window_size)

                    num_ticks = 11
                    tick_positions = np.linspace(0, window_size, num_ticks)
                    ax.set_xticks(tick_positions)
                    ax.xaxis.set_major_formatter(FuncFormatter(time_formatter))

                    y_min, y_max = min(channel_values[channel]), max(channel_values[channel])
                    padding = (y_max - y_min) * 0.1 if y_max != y_min else 1000
                    ax.set_ylim(y_min - padding, y_max + padding)

                    step = (y_max - y_min) / 10
                    step = np.ceil(step / 500) * 500
                    ticks = np.arange(np.floor(y_min / step) * step, y_max + step, step)
                    ax.set_yticks(ticks)
                else:
                    ax.set_visible(False)
                axes.append(ax)

            self.figure.subplots_adjust(left=0.05, right=0.85, top=0.95, bottom=0.15, hspace=0.4)
            self.canvas.setMinimumSize(1000, 800)
            self.canvas.draw()
            self.parent.append_to_console(f"Successfully plotted data for {filename} with {num_channels} channels in selected time range")
        except Exception as e:
            logging.error(f"Error plotting data for {filename}: {e}")
            self.parent.append_to_console(f"Error plotting data for {filename}: {str(e)}")
            self.figure.clear()
            self.canvas.draw()

    def get_widget(self):
        return self.widget