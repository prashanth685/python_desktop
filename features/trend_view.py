from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QPushButton, QTextEdit,QMessageBox
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TrendViewFeature:
    def __init__(self, parent, db, project_name):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.widget = QWidget()
        self.mqtt_tag = None
        self.timer = QTimer(self.widget)
        self.timer.timeout.connect(self.update_plot)
        self.figure = plt.Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        header = QLabel(f"TREND VIEW FOR {self.project_name.upper()}")
        header.setStyleSheet("color: white; font-size: 26px; font-weight: bold; padding: 8px;")
        layout.addWidget(header, alignment=Qt.AlignCenter)

        self.feature_widget = QWidget()
        self.feature_layout = QVBoxLayout()
        self.feature_widget.setLayout(self.feature_layout)
        self.feature_widget.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px;")

        tag_layout = QHBoxLayout()
        tag_label = QLabel("Select Tag:")
        tag_label.setStyleSheet("color: white; font-size: 14px;")
        self.tag_combo = QComboBox()
        tags_data = list(self.db.tags_collection.find({"project_name": self.project_name}))
        if not tags_data:
            self.tag_combo.addItem("No Tags Available")
        else:
            for tag in tags_data:
                self.tag_combo.addItem(tag["tag_name"])
        self.tag_combo.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #1a73e8; padding: 5px;")
        tag_layout.addWidget(tag_label)
        tag_layout.addWidget(self.tag_combo)
        tag_layout.addStretch()
        self.feature_layout.addLayout(tag_layout)

        button_layout = QHBoxLayout()
        mqtt_btn = QPushButton("Start MQTT Plotting")
        mqtt_btn.setStyleSheet("""
            QPushButton { background-color: #f39c12; color: white; border: none; padding: 5px; border-radius: 5px; }
            QPushButton:hover { background-color: #e67e22; }
        """)
        mqtt_btn.clicked.connect(self.start_mqtt_plotting)
        button_layout.addWidget(mqtt_btn)
        button_layout.addStretch()
        self.feature_layout.addLayout(button_layout)

        self.feature_layout.addWidget(self.canvas)

        self.feature_result = QTextEdit()
        self.feature_result.setReadOnly(True)
        self.feature_result.setStyleSheet("background-color: #34495e; color: white; border-radius: 5px; padding: 10px;")
        self.feature_result.setText(f"Trend data for {self.project_name}: Select a tag to begin.")
        self.feature_layout.addWidget(self.feature_result)

        layout.addWidget(self.feature_widget)

    def start_mqtt_plotting(self):
        tag_name = self.tag_combo.currentText()
        if not self.project_name or not tag_name or tag_name == "No Tags Available":
            QMessageBox.warning(self.parent, "Error", "No project or valid tag selected for Trend View plotting!")
            return
        self.mqtt_tag = tag_name
        self.timer.stop()
        self.timer.setInterval(1000)
        self.timer.start()

    def update_plot(self):
        if not self.project_name or not self.mqtt_tag:
            self.feature_result.setText("No project or tag selected for Trend View plotting.")
            return

        data = self.db.get_tag_values(self.project_name, self.mqtt_tag)
        if not data:
            self.feature_result.setText(f"No MQTT data received for {self.mqtt_tag} yet.")
            return

        timestamps = [entry["timestamp"] for entry in data]
        values = [entry["values"][-1] for entry in data]
        self.feature_result.setText(f"Trend Data for {self.mqtt_tag}:\nLatest value: {values[-1]} at {timestamps[-1]}")

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(timestamps, values, 'b-')
        ax.set_xlabel('Timestamp')
        ax.set_ylabel('Value (m/s)')
        ax.set_title(f'Trend View for {self.mqtt_tag}')
        ax.grid(True)
        ax.tick_params(axis='x', rotation=45)
        self.canvas.draw()

    def on_data_received(self, tag_name, values):
        if tag_name == self.mqtt_tag:
            self.update_plot()

    def get_widget(self):
        return self.widget