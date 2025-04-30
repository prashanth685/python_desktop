from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton, QTextEdit, QScrollArea, QDateTimeEdit)
from PyQt5.QtCore import Qt, QDateTime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
from datetime import datetime, timedelta
import logging
import re

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeReportFeature:
    def __init__(self, parent, db, project_name):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.widget = QWidget()
        self.figure = plt.Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.initUI()

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

        # File selection
        file_layout = QHBoxLayout()
        file_label = QLabel("Select Saved File:")
        file_label.setStyleSheet("color: white; font-size: 16px;")
        self.file_combo = QComboBox()
        self.file_combo.setStyleSheet("""QComboBox {
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
    }
""")
        self.file_combo.currentTextChanged.connect(self.update_time_labels)

        self.ok_button = QPushButton("OK")
        self.ok_button.setStyleSheet("background-color: #1a73e8; color: white; padding: 15px; border-radius: 5px; font-size:15px;width:100px;border-radius:50%")
        self.ok_button.clicked.connect(self.plot_data)
        self.ok_button.setEnabled(False)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_combo)
        file_layout.addWidget(self.ok_button)
        file_layout.addStretch()
        self.report_layout.addLayout(file_layout)

        # Time range selection
        time_range_layout = QHBoxLayout()
        start_time_label = QLabel("Select Start Time:")
        start_time_label.setStyleSheet("color: white; font-size: 16px;")
        self.start_time_edit = QDateTimeEdit()
        self.start_time_edit.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #1a73e8; padding: 15px;")
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.dateTimeChanged.connect(self.validate_time_range)

        end_time_label = QLabel("Select End Time:")
        end_time_label.setStyleSheet("color: white; font-size: 16px;")
        self.end_time_edit = QDateTimeEdit()
        self.end_time_edit.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #1a73e8; padding: 15px;")
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.dateTimeChanged.connect(self.validate_time_range)

        time_range_layout.addWidget(start_time_label)
        time_range_layout.addWidget(self.start_time_edit)
        time_range_layout.addWidget(end_time_label)
        time_range_layout.addWidget(self.end_time_edit)
        time_range_layout.addStretch()
        self.report_layout.addLayout(time_range_layout)

        # Time labels
        time_info_layout = QHBoxLayout()
        self.start_time_label = QLabel("File Start Time: N/A")
        self.start_time_label.setStyleSheet("color: white; font-size: 16px;")
        self.stop_time_label = QLabel("File Stop Time: N/A")
        self.stop_time_label.setStyleSheet("color: white; font-size: 16px;")
        time_info_layout.addWidget(self.start_time_label)
        time_info_layout.addWidget(self.stop_time_label)
        time_info_layout.addStretch()
        self.report_layout.addLayout(time_info_layout)

        # Plot canvas
        self.report_layout.addWidget(self.canvas)

        # Result text
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("background-color: #34495e; color: white; border-radius: 5px; padding: 10px;")
        self.result_text.setMinimumHeight(100)
        self.result_text.setText("Select a saved file, set time range, and click OK to view data.")
        self.report_layout.addWidget(self.result_text)
        self.report_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.report_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: black; border: none;")
        scroll_area.setMaximumHeight(4000)
        layout.addWidget(scroll_area)

        # Refresh filenames after UI setup
        self.refresh_filenames()

    def refresh_filenames(self):
        """Refresh the list of available filenames in the combo box."""
        self.file_combo.clear()
        try:
            filenames = self.db.get_distinct_filenames(self.project_name)
            if not filenames:
                self.file_combo.addItem("No Files Available")
                self.result_text.setText("No saved files found for this project.")
                self.start_time_label.setText("File Start Time: N/A")
                self.stop_time_label.setText("File Stop Time: N/A")
                self.start_time_edit.setEnabled(False)
                self.end_time_edit.setEnabled(False)
                self.ok_button.setEnabled(False)
                self.figure.clear()
                self.canvas.draw()
            else:
                for filename in filenames:
                    self.file_combo.addItem(filename)
                self.start_time_edit.setEnabled(True)
                self.end_time_edit.setEnabled(True)
                self.ok_button.setEnabled(True)
                self.update_time_labels(self.file_combo.currentText())
        except Exception as e:
            logging.error(f"Error refreshing filenames: {e}")
            self.file_combo.addItem("Error Loading Files")
            self.result_text.setText(f"Error loading saved files: {str(e)}")
            self.start_time_label.setText("File Start Time: N/A")
            self.stop_time_label.setText("File Stop Time: N/A")
            self.start_time_edit.setEnabled(False)
            self.end_time_edit.setEnabled(False)
            self.ok_button.setEnabled(False)
            self.figure.clear()
            self.canvas.draw()

    def update_time_labels(self, filename):
        """Update file start and stop time labels and set default range for time edits."""
        if not filename or filename in ["No Files Available", "Error Loading Files"]:
            self.start_time_label.setText("File Start Time: N/A")
            self.stop_time_label.setText("File Stop Time: N/A")
            self.start_time_edit.setEnabled(False)
            self.end_time_edit.setEnabled(False)
            self.ok_button.setEnabled(False)
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
                self.ok_button.setEnabled(False)
                self.result_text.setText(f"No data found for file: {filename}")
                return

            timestamps = []
            for item in data:
                created_at = item.get("createdAt")
                try:
                    timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if 'Z' in created_at else datetime.fromisoformat(created_at)
                    timestamps.append(timestamp)
                except Exception as e:
                    logging.warning(f"Invalid timestamp in {filename}: {e}")
                    continue

            if timestamps:
                start_time = min(timestamps)
                stop_time = max(timestamps)
                self.start_time_label.setText(f"File Start Time: {start_time.strftime('%H:%M:%S')}")
                self.stop_time_label.setText(f"File Stop Time: {stop_time.strftime('%H:%M:%S')}")
                self.start_time_edit.setEnabled(True)
                self.end_time_edit.setEnabled(True)
                self.ok_button.setEnabled(True)
                # Set default range to file's full duration
                self.start_time_edit.setDateTime(QDateTime(start_time))
                self.end_time_edit.setDateTime(QDateTime(stop_time))
            else:
                self.start_time_label.setText("File Start Time: N/A")
                self.stop_time_label.setText("File Stop Time: N/A")
                self.start_time_edit.setEnabled(False)
                self.end_time_edit.setEnabled(False)
                self.ok_button.setEnabled(False)
        except Exception as e:
            logging.error(f"Error updating time labels for {filename}: {e}")
            self.start_time_label.setText("File Start Time: N/A")
            self.stop_time_label.setText("File Stop Time: N/A")
            self.start_time_edit.setEnabled(False)
            self.end_time_edit.setEnabled(False)
            self.ok_button.setEnabled(False)
            self.result_text.setText(f"Error loading time data for {filename}: {str(e)}")

    def validate_time_range(self):
        """Validate the selected time range."""
        start_time = self.start_time_edit.dateTime().toPyDateTime()
        end_time = self.end_time_edit.dateTime().toPyDateTime()
        if start_time >= end_time:
            self.ok_button.setEnabled(False)
            self.result_text.setText("Error: Start time must be before end time.")
        else:
            self.ok_button.setEnabled(True)

    def plot_data(self):
        """Plot data for the selected filename within the specified time range, replicating TimeView style with hh:mm:sss x-axis."""
        filename = self.file_combo.currentText()
        if not filename or filename in ["No Files Available", "Error Loading Files"]:
            self.result_text.setText("No valid file selected to plot.")
            self.figure.clear()
            self.canvas.draw()
            return

        # Get user-selected time range
        start_time = self.start_time_edit.dateTime().toPyDateTime()
        end_time = self.end_time_edit.dateTime().toPyDateTime()
        if start_time >= end_time:
            self.result_text.setText("Error: Start time must be before end time.")
            self.figure.clear()
            self.canvas.draw()
            return

        self.figure.clear()
        try:
            # Fetch data sorted by frameIndex
            data = list(self.db.timeview_collection.find(
                {"filename": filename, "project_name": self.project_name}
            ).sort("frameIndex", 1))
            
            if not data:
                self.result_text.setText(f"No data found for file: {filename}")
                self.figure.clear()
                self.canvas.draw()
                return

            # Get number of channels and sampling rate
            num_channels = data[0].get("numberOfChannels", 1)
            data_rate = data[0].get("samplingRate", 4096.0)  # Default to 4096 Hz as in TimeView
            if not isinstance(num_channels, int) or num_channels < 1:
                self.result_text.setText(f"Invalid number of channels ({num_channels}) for file: {filename}")
                self.figure.clear()
                self.canvas.draw()
                return

            # Initialize lists for each channel's values and time points
            channel_values = [[] for _ in range(num_channels)]
            time_points = []
            timestamps = []
            current_time_offset = 0

            for item in data:
                values = item.get("message", [])
                if not values:
                    logging.warning(f"Empty message in frame {item.get('frameIndex')} for {filename}")
                    self.result_text.append(f"Warning: Empty message in frame {item.get('frameIndex')} for {filename}")
                    continue
                
                # Parse createdAt timestamp
                try:
                    created_at = item.get("createdAt")
                    if not created_at:
                        raise ValueError("Missing createdAt field")
                    timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if 'Z' in created_at else datetime.fromisoformat(created_at)
                except Exception as e:
                    logging.error(f"Invalid createdAt timestamp in frame {item.get('frameIndex')}: {e}")
                    self.result_text.append(f"Error: Invalid timestamp in frame {item.get('frameIndex')} for {filename}")
                    continue

                # Skip if timestamp is outside the selected range
                if timestamp < start_time or timestamp > end_time:
                    continue

                # Check if values are divisible by number of channels
                if len(values) % num_channels != 0:
                    logging.warning(f"Invalid data in frame {item.get('frameIndex')}: {len(values)} values not divisible by {num_channels} channels")
                    self.result_text.append(f"Warning: Invalid data in frame {item.get('frameIndex')}: {len(values)} values not divisible by {num_channels} channels")
                    continue

                num_samples = len(values) // num_channels
                # Distribute values to channels and generate time points
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
                                self.result_text.append(f"Warning: Invalid value at frame {item.get('frameIndex')}, channel {channel + 1}")
                current_time_offset += num_samples / data_rate

            if not time_points or not any(channel_values):
                self.result_text.setText(f"No data found in the selected time range for file: {filename}")
                self.figure.clear()
                self.canvas.draw()
                return

            # Create subplots for each channel, replicating TimeView style
            axes = []
            lines = []
            window_size = max(time_points) if time_points else 1.0

            # Formatter for x-axis to display hh:mm:sss
            def time_formatter(x, pos):
                # Convert seconds offset to actual timestamp
                actual_time = start_time + timedelta(seconds=x)
                return actual_time.strftime('%H:%M:%S.%f')[:-3]  # hh:mm:ss.sss

            for channel in range(num_channels):
                ax = self.figure.add_subplot(num_channels, 1, channel + 1)
                if channel_values[channel]:
                    line, = ax.plot(time_points, channel_values[channel], f'C{channel}-', linewidth=1.5)
                    lines.append(line)
                    ax.grid(True, linestyle='--', alpha=0.7)
                    ax.set_ylabel(f"Channel {channel + 1}", rotation=90, labelpad=10)
                    ax.yaxis.set_label_position("right")
                    ax.yaxis.tick_right()
                    ax.set_xlabel("Time (hh:mm:ss.sss)")
                    ax.set_xlim(0, window_size)

                    # Set x-axis ticks and formatter
                    num_ticks = 11
                    tick_positions = np.linspace(0, window_size, num_ticks)
                    ax.set_xticks(tick_positions)
                    ax.xaxis.set_major_formatter(FuncFormatter(time_formatter))

                    # Set y-axis limits with padding
                    y_min, y_max = min(channel_values[channel]), max(channel_values[channel])
                    padding = (y_max - y_min) * 0.1 if y_max != y_min else 1000
                    ax.set_ylim(y_min - padding, y_max + padding)

                    # Generate y-ticks similar to TimeView
                    step = (y_max - y_min) / 10
                    step = np.ceil(step / 500) * 500
                    ticks = np.arange(np.floor(y_min / step) * step, y_max + step, step)
                    ax.set_yticks(ticks)
                else:
                    ax.set_visible(False)  # Hide empty subplots
                axes.append(ax)

            self.figure.subplots_adjust(left=0.05, right=0.85, top=0.95, bottom=0.15, hspace=0.4)
            self.canvas.setMinimumSize(1000, 800)
            self.canvas.draw()
            self.result_text.append(f"Successfully plotted data for {filename} with {num_channels} channels in selected time range")
        except Exception as e:
            logging.error(f"Error plotting data for {filename}: {e}")
            self.result_text.setText(f"Error plotting data for {filename}: {str(e)}")
            self.figure.clear()
            self.canvas.draw()

    def get_widget(self):
        return self.widget