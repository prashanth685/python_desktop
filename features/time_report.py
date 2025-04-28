from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton, QTextEdit, QScrollArea)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
import logging

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
        self.file_combo.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #1a73e8; padding: 15px;")
        self.refresh_filenames()
        self.file_combo.currentTextChanged.connect(self.plot_data)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_combo)
        file_layout.addStretch()
        self.report_layout.addLayout(file_layout)

        # Plot canvas
        self.report_layout.addWidget(self.canvas)

        # Result text
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("background-color: #34495e; color: white; border-radius: 5px; padding: 10px;")
        self.result_text.setMinimumHeight(50)
        self.report_layout.addWidget(self.result_text)
        self.report_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.report_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: black; border: none;")
        scroll_area.setMaximumHeight(4000)
        layout.addWidget(scroll_area)

    def refresh_filenames(self):
        self.file_combo.clear()
        filenames = self.db.timeview_collection.distinct("filename", {"project_name": self.project_name})
        if not filenames:
            self.file_combo.addItem("No Files Available")
        else:
            for filename in sorted(filenames):
                self.file_combo.addItem(filename)

    def plot_data(self, filename):
        if not filename or filename == "No Files Available":
            self.result_text.setText("No data available to plot.")
            self.figure.clear()
            self.canvas.draw()
            return

        self.figure.clear()
        data = list(self.db.timeview_collection.find({"filename": filename, "project_name": self.project_name}).sort("frameIndex", 1))
        
        if not data:
            self.result_text.setText(f"No data found for {filename}")
            self.canvas.draw()
            return

        # Get number of channels
        num_channels = data[0].get("numberOfChannels", 1)
        sampling_rate = data[0].get("samplingRate", 4096.0)

        # Collect all values and timestamps
        all_values = []
        all_timestamps = []
        for item in data:
            values = item.get("message", [])
            timestamp = datetime.fromisoformat(item.get("createdAt").replace('Z', '+00:00')) if 'Z' in item.get("createdAt") else datetime.fromisoformat(item.get("createdAt"))
            num_samples = len(values) // num_channels
            timestamps = [timestamp + timedelta(seconds=i / sampling_rate) for i in range(num_samples)]
            all_values.extend(values)
            all_timestamps.extend(timestamps)

        if not all_values:
            self.result_text.setText("No valid data to plot.")
            self.canvas.draw()
            return

        # Create subplots for each channel
        for channel in range(num_channels):
            ax = self.figure.add_subplot(num_channels, 1, channel + 1)
            channel_values = all_values[channel::num_channels]
            ax.plot(all_timestamps, channel_values, 'b-', linewidth=1.5)
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.set_ylabel(f"Channel {channel + 1}")
            ax.set_xlabel("Time")

            # Format x-axis to show HH:MM:SS.mmm
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.tick_params(axis='x', rotation=0, labelsize=8)
            
            # Set y-axis limits
            if channel_values:
                y_min, y_max = min(channel_values), max(channel_values)
                padding = (y_max - y_min) * 0.1 if y_max != y_min else 1000
                ax.set_ylim(y_min - padding, y_max + padding)

        self.figure.subplots_adjust(left=0.1, right=0.9, top=0.95, bottom=0.2, hspace=0.4)
        self.canvas.draw()
        self.result_text.setText(f"Plotted data for {filename} with {num_channels} channels")

    def get_widget(self):
        return self.widget