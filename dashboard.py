import sys
import gc
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
                             QSplitter, QToolBar, QAction, QTreeWidget, QTreeWidgetItem,
                             QInputDialog, QMessageBox, QSizePolicy, QApplication,
                             QTextEdit, QGridLayout, QDialog, QDialogButtonBox,
                             QScrollArea, QComboBox)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon, QColor
import os
import logging
import uuid

# Assuming these are defined in your codebase
from mqtthandler import MQTTHandler
from features.create_tags import CreateTagsFeature
from features.tabular_view import TabularViewFeature
from features.time_view import TimeViewFeature
from features.fft_view import FFTViewFeature
from features.waterfall import WaterfallFeature
from features.orbit import OrbitFeature
from features.trend_view import TrendViewFeature
from features.multi_trend import MultiTrendFeature
from features.bode_plot import BodePlotFeature
from features.history_plot import HistoryPlotFeature
from features.time_report import TimeReportFeature
from features.report import ReportFeature

class FeatureWindow(QWidget):
    def __init__(self, feature_instance, feature_name, parent=None, width=300, height=200):
        super().__init__(parent)
        self.feature_instance = feature_instance
        self.feature_name = feature_name
        self.is_minimized = False
        self.is_maximized = False
        self.normal_size = QSize(width, height)
        self.minimized_size = QSize(width, 30)
        self.maximized_size = None
        self.previous_grid_state = []  # Stores (widget, row, col, rowspan, colspan)
        self.previous_scroll_position = 0
        self.previous_grid_layout = None
        self.content_widget = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        self.setLayout(layout)

        # Title bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        title_label = QLabel(self.feature_name)
        title_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold; padding: 5px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Buttons
        self.minimize_button = QPushButton("🗕")
        self.minimize_button.clicked.connect(self.minimize_window)
        self.minimize_button.setStyleSheet("""
            QPushButton { 
                color: black; 
                font-size: 14px; 
                padding: 2px 8px; 
                border: none;
                background: #d3d3d3;
                border-radius: 4px;
            }
            QPushButton:hover { background: #e0e0e0; }
            QPushButton:pressed { background: #c0c0c0; }
        """)

        self.maximize_button = QPushButton("🗖")
        self.maximize_button.clicked.connect(self.maximize_window)
        self.maximize_button.setStyleSheet("""
            QPushButton { 
                color: black; 
                font-size: 14px; 
                padding: 2px 8px; 
                border: none;
                background: #d3d3d3;
                border-radius: 4px;
            }
            QPushButton:hover { background: #e0e0e0; }
            QPushButton:pressed { background: #c0c0c0; }
        """)

        self.close_button = QPushButton("🗙")
        self.close_button.clicked.connect(self.close_window)
        self.close_button.setStyleSheet("""
            QPushButton { 
                color: white; 
                font-size: 14px; 
                padding: 2px 8px; 
                border: none;
                background: #ff4040;
                border-radius: 4px;
            }
            QPushButton:hover { background: #ff6666; }
            QPushButton:pressed { background: #cc3333; }
        """)

        header_layout.addWidget(self.minimize_button)
        header_layout.addWidget(self.maximize_button)
        header_layout.addWidget(self.close_button)

        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        header_widget.setStyleSheet("""
            QWidget { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0055ff, stop:1 #00aaff); 
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
        """)
        layout.addWidget(header_widget)

        # Feature content
        self.content_widget = self.feature_instance.get_widget()
        if self.content_widget:
            self.content_widget.show()
            layout.addWidget(self.content_widget)
        else:
            error_label = QLabel("Feature not available")
            error_label.setStyleSheet("color: #ecf0f1; font-size: 14px;")
            layout.addWidget(error_label)

        self.setStyleSheet("""
            QWidget { 
                background-color: #2c3e50; 
                border: 1px solid #34495e; 
                border-radius: 6px;
            }
        """)
        self.setFixedSize(self.normal_size)

    def minimize_window(self):
        if not self.is_minimized and not self.is_maximized:
            self.setFixedSize(self.minimized_size)
            self.is_minimized = True
            if self.content_widget:
                self.content_widget.hide()
            self.minimize_button.setEnabled(False)
            logging.info(f"Minimized window: {self.feature_name}")

            dashboard = self.get_dashboard_parent()
            if dashboard:
                dashboard.resize_grid()

    def maximize_window(self):
        dashboard = self.get_dashboard_parent()
        if not dashboard:
            logging.error("Could not find DashboardWindow parent")
            return

        if not self.is_maximized:
            # Save current grid state
            self.previous_grid_state = []
            self.previous_grid_layout = dashboard.current_grid_layout
            if dashboard.grid_layout:
                for i in range(dashboard.grid_layout.count()):
                    item = dashboard.grid_layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        pos = dashboard.grid_layout.getItemPosition(i)
                        if widget != self:
                            self.previous_grid_state.append((widget, pos[0], pos[1], pos[2], pos[3]))
                            widget.hide()

            # Save scroll position
            if dashboard.scroll_area and dashboard.scroll_area.verticalScrollBar():
                self.previous_scroll_position = dashboard.scroll_area.verticalScrollBar().value()

            # Maximize
            content_width = dashboard.content_container.width() - 20
            content_height = dashboard.content_container.height() - dashboard.console.height() - 20
            self.maximized_size = QSize(content_width, content_height)
            self.setMinimumSize(self.maximized_size)
            self.setMaximumSize(QSize(16777215, 16777215))
            self.is_maximized = True
            self.is_minimized = False
            self.minimize_button.setEnabled(True)
            self.maximize_button.setText("🗗")
            self.maximize_button.setToolTip("Restore Window")

            # Replace grid with this window inside scroll area
            dashboard.clear_content_layout()
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setStyleSheet("QScrollArea { background-color: #263238; border: none; }")
            scroll_area.setWidget(self)
            dashboard.content_layout.addWidget(scroll_area)
            dashboard.scroll_area = scroll_area
            self.show()
            logging.info(f"Maximized window: {self.feature_name}")
        else:
            self.restore_grid(dashboard)

    def restore_grid(self, dashboard):
        try:
            # Reset states
            self.is_maximized = False
            self.is_minimized = False
            self.minimize_button.setEnabled(True)
            self.maximize_button.setText("🗖")
            self.maximize_button.setToolTip("Maximize Window")

            # Clear current layout
            dashboard.clear_content_layout()

            # Restore grid
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setStyleSheet("QScrollArea { background-color: #263238; border: none; }")
            scroll_widget = QWidget()
            dashboard.grid_layout = QGridLayout()
            dashboard.grid_layout.setContentsMargins(10, 10, 10, 10)
            dashboard.grid_layout.setSpacing(10)
            scroll_widget.setLayout(dashboard.grid_layout)
            scroll_area.setWidget(scroll_widget)
            dashboard.content_layout.addWidget(scroll_area)
            dashboard.scroll_area = scroll_area

            # Calculate sizes
            rows, cols = map(int, self.previous_grid_layout.split('x'))
            content_width = dashboard.content_container.width() - 30
            content_height = dashboard.content_container.height() - dashboard.console.height() - 20
            vertical_gap = dashboard.grid_layout.verticalSpacing()
            total_gaps_height = vertical_gap * (rows - 1) if rows > 1 else 0
            window_width = max(200, (content_width - (cols - 1) * 10 - 20) // cols)
            available_height = content_height - total_gaps_height
            window_height = max(150, available_height // rows)

            # Restore this window first
            self.normal_size = QSize(window_width, window_height)
            self.minimized_size = QSize(window_width, 30)
            self.setFixedSize(self.normal_size)
            dashboard.grid_layout.addWidget(self, 0, 0)
            self.show()

            # Restore other widgets
            for widget, row, col, rowspan, colspan in self.previous_grid_state:
                try:
                    if widget and isinstance(widget, FeatureWindow) and not widget.isHidden():
                        widget.normal_size = QSize(window_width, window_height)
                        widget.minimized_size = QSize(window_width, 30)
                        widget.setFixedSize(widget.normal_size if not widget.is_minimized else widget.minimized_size)
                        dashboard.grid_layout.addWidget(widget, row, col, rowspan, colspan)
                        widget.show()
                    else:
                        logging.warning(f"Skipping invalid or hidden widget at row {row}, col {col}")
                except RuntimeError as e:
                    logging.error(f"Error restoring widget at row {row}, col {col}: {str(e)}")
                    continue

            # Fill empty cells
            for row in range(rows):
                for col in range(cols):
                    if not dashboard.grid_layout.itemAtPosition(row, col):
                        empty_widget = QWidget()
                        empty_widget.setStyleSheet("background-color: transparent;")
                        empty_widget.setFixedSize(window_width, window_height)
                        dashboard.grid_layout.addWidget(empty_widget, row, col)
                        empty_widget.show()

            # Set scroll widget size
            total_windows_height = (window_height * rows) + total_gaps_height
            scroll_widget.setMinimumSize(content_width, total_windows_height + 20)

            # Restore scroll position
            if dashboard.scroll_area and dashboard.scroll_area.verticalScrollBar():
                dashboard.scroll_area.verticalScrollBar().setValue(self.previous_scroll_position)

            # Update dashboard state
            dashboard.current_grid_layout = self.previous_grid_layout
            if dashboard.grid_label:
                dashboard.grid_label.setText(self.previous_grid_layout)

            dashboard.content_container.update()
            logging.info(f"Restored grid for window: {self.feature_name} with layout {self.previous_grid_layout}")
        except Exception as e:
            logging.error(f"Error restoring grid for {self.feature_name}: {str(e)}")
            QMessageBox.warning(dashboard, "Error", f"Error restoring grid: {str(e)}")

    def close_window(self):
        try:
            if self.feature_instance:
                if hasattr(self.feature_instance, 'cleanup'):
                    self.feature_instance.cleanup()
                if self.content_widget:
                    self.content_widget.setParent(None)
                    self.content_widget.deleteLater()

            self.setParent(None)
            self.deleteLater()

            dashboard = self.get_dashboard_parent()
            if dashboard:
                if self.feature_name in dashboard.feature_instances:
                    del dashboard.feature_instances[self.feature_name]
                feature_names = [name for name, instance in dashboard.feature_instances.items() if instance]
                dashboard.display_features(feature_names, dashboard.current_grid_layout)
        except Exception as e:
            logging.error(f"Error closing window {self.feature_name}: {str(e)}")

    def get_dashboard_parent(self):
        dashboard = self.parent()
        while dashboard and not isinstance(dashboard, DashboardWindow):
            dashboard = dashboard.parent()
        return dashboard

class CustomizeFeaturesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Customize Grid Layout")
        self.grid_layout = "1x2"
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        layout_label = QLabel("Select Grid Layout (Rows x Columns):")
        layout_label.setStyleSheet("color: #ecf0f1; font-size: 16px; padding-bottom: 5px;")
        layout.addWidget(layout_label)

        self.grid_combo = QComboBox()
        grid_options = ["1x1", "1x2", "1x3", "2x2", "2x3", "3x3"]
        self.grid_combo.addItems(grid_options)
        self.grid_combo.setStyleSheet("""
            QComboBox {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #4a90e2;
                padding: 8px;
                border-radius: 4px;
                font-size: 15px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                width: 10px;
                height: 10px;
            }
        """)
        layout.addWidget(self.grid_combo)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setStyleSheet("""
            QDialog { 
                background-color: #1e2937; 
                color: white; 
                font-size: 16px; 
                border: 1px solid #2c3e50; 
                border-radius: 8px; 
                padding: 15px;
            }
            QDialogButtonBox QPushButton { 
                background-color: #4a90e2; 
                color: white; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 5px; 
                font-size: 15px; 
                min-width: 80px; 
            }
            QDialogButtonBox QPushButton:hover { 
                background-color: #357abd; 
            }
            QDialogButtonBox QPushButton:pressed { 
                background-color: #2c5d9b; 
            }
        """)

        self.setFixedSize(300, 200)

    def accept(self):
        self.grid_layout = self.grid_combo.currentText()
        super().accept()

class DashboardWindow(QWidget):
    def __init__(self, db, email, project_name, project_selection_window):
        super().__init__()
        self.db = db
        self.email = email
        self.current_project = project_name
        self.project_selection_window = project_selection_window
        self.current_feature = None
        self.mqtt_handler = None
        self.feature_instances = {}
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.is_saving = False
        self.mqtt_connected = False
        self.fft_window = None
        self.grid_layout = None
        self.current_grid_layout = "1x1"
        self.grid_label = None
        self.scroll_area = None
        self.initUI()
        QTimer.singleShot(0, self.deferred_initialization)

    def deferred_initialization(self):
        try:
            self.load_project_features()
            self.setup_mqtt()
            self.display_features(["Create Tags"], self.current_grid_layout)
        except Exception as e:
            logging.error(f"Error in deferred initialization: {str(e)}")
            QMessageBox.warning(self, "Error", f"Initialization error: {str(e)}")

    def setup_mqtt(self):
        if not self.current_project:
            logging.warning("No project selected for MQTT setup")
            return

        self.cleanup_mqtt()

        try:
            tags = self.get_project_tags()
            if tags:
                self.mqtt_handler = MQTTHandler(self.db, self.current_project)
                self.mqtt_handler.data_received.connect(self.on_data_received)
                self.mqtt_handler.connection_status.connect(self.on_mqtt_status)
                self.mqtt_handler.start()
                self.mqtt_connected = True
                logging.info(f"MQTT setup for project: {self.current_project}")
                self.append_to_console(f"MQTT setup for project: {self.current_project}")
            else:
                logging.warning(f"No tags found for project: {self.current_project}")
                self.mqtt_connected = False
        except Exception as e:
            logging.error(f"Failed to setup MQTT: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to setup MQTT: {str(e)}")
            self.append_to_console(f"Failed to setup MQTT: {str(e)}")

        self.update_subtoolbar()

    def cleanup_mqtt(self):
        if self.mqtt_handler:
            try:
                self.mqtt_handler.data_received.disconnect()
                self.mqtt_handler.connection_status.disconnect()
                self.mqtt_handler.stop()
                self.mqtt_handler.deleteLater()
                logging.info("Previous MQTT handler stopped")
            except Exception as e:
                logging.error(f"Error stopping MQTT handler: {str(e)}")
            finally:
                self.mqtt_handler = None
                self.mqtt_connected = False

    def get_project_tags(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            tags = list(self.db.tags_collection.find({"project_name": self.current_project}))
            return [tag["tag_name"] for tag in tags]
        except Exception as e:
            logging.error(f"Failed to retrieve project tags: {str(e)}")
            return []

    def connect_mqtt(self):
        if self.mqtt_connected:
            self.append_to_console("Already connected to MQTT")
            return

        try:
            tags = self.get_project_tags()
            if not tags:
                QMessageBox.warning(self, "Error", "No tags found for this project. Please create tags first!")
                self.append_to_console("No tags found for project")
                return

            self.cleanup_mqtt()
            self.mqtt_handler = MQTTHandler(self.db, self.current_project)
            self.mqtt_handler.data_received.connect(self.on_data_received)
            self.mqtt_handler.connection_status.connect(self.on_mqtt_status)
            self.mqtt_handler.start()
            self.mqtt_connected = True
            self.update_subtoolbar()

            logging.info(f"MQTT connected for project: {self.current_project}")
            self.append_to_console(f"MQTT connected for project: {self.current_project}")
        except Exception as e:
            logging.error(f"Failed to connect MQTT: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to connect MQTT: {str(e)}")
            self.append_to_console(f"Failed to connect MQTT: {str(e)}")
            self.mqtt_connected = False
            self.update_subtoolbar()

    def disconnect_mqtt(self):
        if not self.mqtt_connected:
            self.append_to_console("Already disconnected from MQTT")
            return

        try:
            self.cleanup_mqtt()
            self.update_subtoolbar()
            logging.info(f"MQTT disconnected for project: {self.current_project}")
            self.append_to_console(f"MQTT disconnected for project: {self.current_project}")
        except Exception as e:
            logging.error(f"Failed to disconnect MQTT: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to disconnect MQTT: {str(e)}")
            self.append_to_console(f"Failed to disconnect MQTT: {str(e)}")
            self.update_subtoolbar()

    def on_data_received(self, tag_name, values):
        if self.current_feature and self.current_project:
            feature_instance = self.feature_instances.get(self.current_feature)
            if feature_instance and hasattr(feature_instance, 'on_data_received'):
                try:
                    feature_instance.on_data_received(tag_name, values)
                except Exception as e:
                    logging.error(f"Error in on_data_received for {self.current_feature}: {str(e)}")

        for feature_name, instance in self.feature_instances.items():
            if hasattr(instance, 'on_data_received'):
                try:
                    instance.on_data_received(tag_name, values)
                except Exception as e:
                    logging.error(f"Error in on_data_received for feature {feature_name}: {str(e)}")

    def on_mqtt_status(self, message):
        self.mqtt_connected = "Connected" in message
        self.append_to_console(f"MQTT Status: {message}")
        self.update_subtoolbar()

    def append_to_console(self, text):
        if "MQTT" in text or "mqtt" in text:
            if hasattr(self, 'console'):
                self.console.append(text)
                self.console.ensureCursorVisible()

    def initUI(self):
        self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
        self.setWindowState(Qt.WindowMaximized)

        app = QApplication.instance()
        app.setStyleSheet("""
            QInputDialog, QMessageBox, QDialog {
                background-color: #1e2937;
                color: white;
                font-size: 16px;
                border: 1px solid #2c3e50;
                border-radius: 8px;
                padding: 15px;
            }
            QInputDialog QLineEdit {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #4a90e2;
                padding: 8px;
                border-radius: 4px;
                font-size: 15px;
            }
            QInputDialog QLabel,
            QMessageBox QLabel {
                color: #ecf0f1;
                font-size: 16px;
                padding-bottom: 10px;
            }
            QInputDialog QPushButton,
            QMessageBox QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 15px;
                min-width: 80px;
            }
            QInputDialog QPushButton:hover,
            QMessageBox QPushButton:hover {
                background-color: #357abd;
            }
            QInputDialog QPushButton:pressed,
            QMessageBox QPushButton:pressed {
                background-color: #2c5d9b;
            }
            QScrollBar:vertical {
                border: none;
                background: #263238;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #4a90e2;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #357abd;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        # File toolbar
        self.file_bar = QToolBar("File")
        self.file_bar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f5f5f5, stop:1 #e0e0e0);
                border: none;
                padding: 0;
                spacing: 5px;
            }
            QToolBar QToolButton {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                padding: 8px 12px;
                border-radius: 4px;
                background-color: transparent;
            }
            QToolBar QToolButton:hover {
                background-color: #4a90e2;
                color: white;
            }
        """)
        self.file_bar.setFixedHeight(40)
        self.file_bar.setMovable(False)
        self.file_bar.setFloatable(False)

        actions = [
            ("Home", "Go to Dashboard Home", self.display_dashboard),
            ("Open", "Open an Existing Project", self.open_project),
            ("New", "Create a New Project", self.create_project),
            ("Settings", "Open Application Settings", self.settings_action),
            ("Refresh", "Refresh Current View", self.refresh_action),
            ("Exit", "Exit Application", self.close)
        ]

        for text, tooltip, func in actions:
            action = QAction(text, self)
            action.setToolTip(tooltip)
            action.triggered.connect(func)
            self.file_bar.addAction(action)

        main_layout.addWidget(self.file_bar)

        # Feature toolbar
        self.toolbar = QToolBar("Features")
        self.toolbar.setFixedHeight(75)
        self.update_toolbar()
        main_layout.addWidget(self.toolbar)

        # Main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setContentsMargins(0, 0, 0, 0)
        main_splitter.setHandleWidth(1)
        main_splitter.setStyleSheet("QSplitter::handle { background-color: #2c3e50; }")
        main_layout.addWidget(main_splitter)

        # Left panel - Tree widget
        self.tree = QTreeWidget()
        self.tree.header().hide()
        self.tree.setStyleSheet("""
            QTreeWidget { 
                background-color: #1e2937; 
                color: #ecf0f1; 
                border: none; 
                font-size: 16px; 
            }
            QTreeWidget::item { 
                padding: 8px; 
                border-bottom: 1px solid #2c3e50; 
            }
            QTreeWidget::item:hover { 
                background-color: #34495e; 
            }
            QTreeWidget::item:selected { 
                background-color: #4a90e2; 
                color: white; 
            }
        """)
        self.tree.setFixedWidth(250)
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        main_splitter.addWidget(self.tree)

        # Right container
        right_container = QWidget()
        right_container.setStyleSheet("background-color: #263238;")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_container.setLayout(right_layout)

        # Subtoolbar container
        subtoolbar_container = QWidget()
        subtoolbar_container.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eceff1, stop:1 #cfd8dc);")
        subtoolbar_layout = QHBoxLayout()
        subtoolbar_layout.setContentsMargins(10, 0, 10, 0)
        subtoolbar_layout.setSpacing(10)
        subtoolbar_container.setLayout(subtoolbar_layout)

        self.subtoolbar = QToolBar("Controls")
        self.subtoolbar.setFixedHeight(100)
        subtoolbar_layout.addWidget(self.subtoolbar)
        self.update_subtoolbar()
        right_layout.addWidget(subtoolbar_container)

        # Content area
        self.content_container = QWidget()
        self.content_container.setStyleSheet("background-color: #263238;")
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_container.setLayout(self.content_layout)
        right_layout.addWidget(self.content_container, 1)

        # Console
        console_container = QWidget()
        console_layout = QVBoxLayout()
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.setSpacing(0)
        console_container.setLayout(console_layout)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        button_layout.addWidget(spacer)

        clear_button = QPushButton("Clear")
        clear_button.setToolTip("Clear Console Output")
        clear_button.clicked.connect(self.clear_console)
        clear_button.setStyleSheet("""
            QPushButton { 
                color: white; 
                font-size: 14px; 
                padding: 2px 8px; 
                border-radius: 4px; 
                background-color: #d32f2f; 
                border: none;
            }
            QPushButton:hover { background-color: #ef5350; }
            QPushButton:pressed { background-color: #b71c1c; }
        """)
        button_layout.addWidget(clear_button)

        minimize_button = QPushButton("⏷")
        minimize_button.setToolTip("Minimize Console")
        minimize_button.clicked.connect(self.minimize_console)
        minimize_button.setStyleSheet("""
            QPushButton { 
                color: white; 
                font-size: 16px; 
                padding: 2px 8px; 
                border-radius: 4px; 
                background-color: #34495e; 
                border: none;
            }
            QPushButton:hover { background-color: #4a90e2; }
            QPushButton:pressed { background-color: #357abd; }
        """)
        button_layout.addWidget(minimize_button)

        maximize_button = QPushButton("⏶")
        maximize_button.setToolTip("Maximize Console")
        maximize_button.clicked.connect(self.maximize_console)
        maximize_button.setStyleSheet("""
            QPushButton { 
                color: white; 
                font-size: 16px; 
                padding: 2px 8px; 
                border-radius: 4px; 
                background-color: #34495e; 
                border: none;
            }
            QPushButton:hover { background-color: #4a90e2; }
            QPushButton:pressed { background-color: #357abd; }
        """)
        button_layout.addWidget(maximize_button)

        console_layout.addLayout(button_layout)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(50)
        self.console.setStyleSheet("""
            QTextEdit { 
                background-color: #212121; 
                color: #e0e0e0; 
                border: none; 
                font-family: Consolas, monospace; 
                font-size: 14px; 
                padding: 10px; 
            }
        """)
        console_layout.addWidget(self.console)

        right_layout.addWidget(console_container, 0)
        main_splitter.addWidget(right_container)
        main_splitter.setSizes([250, 950])

    def clear_console(self):
        try:
            self.console.clear()
            logging.info("Console cleared")
        except Exception as e:
            logging.error(f"Error clearing console: {str(e)}")

    def minimize_console(self):
        try:
            self.console.setFixedHeight(50)
            logging.info("Console minimized to 50px")
            self.resize_grid()
        except Exception as e:
            logging.error(f"Error minimizing console: {str(e)}")

    def maximize_console(self):
        try:
            self.console.setFixedHeight(150)
            logging.info("Console maximized to 150px")
            self.resize_grid()
        except Exception as e:
            logging.error(f"Error maximizing console: {str(e)}")

    def update_file_bar(self):
        try:
            self.file_bar.setStyleSheet("""
                QToolBar {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f5f5f5, stop:1 #e0e0e0);
                    border: none;
                    padding: 0;
                    spacing: 5px;
                }
                QToolBar QToolButton {
                    font-size: 18px;
                    font-weight: bold;
                    color: #333;
                    padding: 8px 12px;
                    border-radius: 4px;
                    background-color: transparent;
                }
                QToolBar QToolButton:hover {
                    background-color: #4a90e2;
                    color: white;
                }
            """)
        except Exception as e:
            logging.error(f"Error updating file bar: {str(e)}")

    def update_toolbar(self):
        self.toolbar.clear()
        self.toolbar.setStyleSheet("""
            QToolBar { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #37474f, stop:1 #263238); 
                border: none; 
                padding: 5px; 
                spacing: 10px; 
            }
            QToolButton { 
                border: none; 
                padding: 10px; 
                border-radius: 6px; 
                background-color: #455a64; 
                font-size: 35px; 
                color: #eceff1; 
            }
            QToolButton:hover { 
                background-color: #4a90e2; 
            }
            QToolButton:pressed { 
                background-color: #357abd; 
            }
            QToolButton:focus { 
                outline: none; 
                border: 1px solid #4a90e2; 
            }
        """)
        self.toolbar.setIconSize(QSize(30, 30))
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)

        def add_action(feature_name, text_icon, color, tooltip):
            action = QAction(text_icon, self)
            action.triggered.connect(lambda: self.add_feature_to_grid(feature_name))
            action.setToolTip(tooltip)
            self.toolbar.addAction(action)
            button = self.toolbar.widgetForAction(action)
            if button:
                button.setStyleSheet(f"""
                    QToolButton {{ 
                        color: {color}; 
                        font-size: 35px; 
                        border: none; 
                        border-radius: 6px; 
                        background-color: #455a64; 
                    }}
                    QToolButton:hover {{ background-color: #4a90e2; }}
                    QToolButton:pressed {{ background-color: #357abd; }}
                """)

        feature_actions = [
            ("Create Tags", "🏷️", "#81c784", "Add Create Tags Feature"),
            ("Time View", "⏱️", "#ffb300", "Add Time View Feature"),
            ("Tabular View", "📋", "#64b5f6", "Add Tabular View Feature"),
            ("Time Report", "📄", "#4db6ac", "Add Time Report Feature"),
            ("FFT", "📈", "#ba68c8", "Add FFT View Feature"),
            ("Waterfall", "🌊", "#4dd0e1", "Add Waterfall Feature"),
            ("Orbit", "🪐", "#f06292", "Add Orbit Feature"),
            ("Trend View", "📉", "#aed581", "Add Trend View Feature"),
            ("Multiple Trend View", "📊", "#ff8a65", "Add Multiple Trend View Feature"),
            ("Bode Plot", "🔍", "#7986cb", "Add Bode Plot Feature"),
            ("History Plot", "🕰️", "#ef5350", "Add History Plot Feature"),
            ("Report", "📝", "#ab47bc", "Add Report Feature"),
        ]

        for feature_name, text_icon, color, tooltip in feature_actions:
            add_action(feature_name, text_icon, color, tooltip)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

    def update_subtoolbar(self):
        self.subtoolbar.clear()
        self.subtoolbar.setStyleSheet("""
            QToolBar { 
                background: transparent; 
                border: none; 
                padding: 5px; 
                spacing: 10px; 
            }
            QToolButton { 
                border: none; 
                padding: 8px; 
                border-radius: 5px; 
                background-color: #90a4ae; 
                font-size: 24px; 
                color: white; 
            }
            QToolButton:hover { 
                background-color: #4a90e2; 
            }
            QToolButton:pressed { 
                background-color: #357abd; 
            }
            QToolButton:disabled { 
                background-color: #546e7a; 
                color: #b0bec5; 
            }
        """)
        self.subtoolbar.setIconSize(QSize(25, 25))
        self.subtoolbar.setMovable(False)
        self.subtoolbar.setFloatable(False)

        def add_action(text_icon, color, callback, tooltip, enabled, background_color):
            action = QAction(text_icon, self)
            action.triggered.connect(callback)
            action.setToolTip(tooltip)
            action.setEnabled(enabled)
            self.subtoolbar.addAction(action)
            button = self.subtoolbar.widgetForAction(action)
            if button:
                button.setStyleSheet(f"""
                    QToolButton {{ 
                        color: {color}; 
                        font-size: 24px; 
                        border: none; 
                        padding: 8px; 
                        border-radius: 5px; 
                        background-color: {background_color}; 
                    }}
                    QToolButton:hover {{ background-color: #4a90e2; }}
                    QToolButton:pressed {{ background-color: #357abd; }}
                    QToolButton:disabled {{ background-color: #546e7a; color: #b0bec5; }}
                """)

        is_time_view = "Time View" in self.feature_instances
        add_action("▶", "#ffffff", self.start_saving, "Start Saving Data (Time View)", is_time_view and not self.is_saving, "#43a047")
        add_action("⏸", "#ffffff", self.stop_saving, "Stop Saving Data (Time View)", is_time_view and self.is_saving, "#ef5350")
        self.subtoolbar.addSeparator()

        connect_bg = "#43a047" if self.mqtt_connected else "#90a4ae"
        disconnect_bg = "#ef5350" if not self.mqtt_connected else "#90a4ae"
        add_action("🟢", "#ffffff", self.connect_mqtt, "Connect to MQTT", not self.mqtt_connected, connect_bg)
        add_action("🔴", "#ffffff", self.disconnect_mqtt, "Disconnect from MQTT", self.mqtt_connected, disconnect_bg)
        self.subtoolbar.addSeparator()

        customize_action = QAction("🎛️", self)
        customize_action.triggered.connect(self.customize_features)
        customize_action.setToolTip("Customize Grid Layout")
        self.subtoolbar.addAction(customize_action)

        customize_button = self.subtoolbar.widgetForAction(customize_action)
        if customize_button:
            customize_button.setStyleSheet("""
                QToolButton { 
                    color: #ffffff; 
                    font-size: 24px; 
                    border: none; 
                    padding: 8px; 
                    border-radius: 5px; 
                    background-color: #0288d1;
                }
                QToolButton:hover { background-color: #4a90e2; }
                QToolButton:pressed { background-color: #357abd; }
            """)

        if not self.grid_label:
            self.grid_label = QLabel(self.current_grid_layout)
        self.grid_label.setText(self.current_grid_layout)
        self.grid_label.setStyleSheet("color: #333; font-size: 14px; margin-left: 5px;")
        self.subtoolbar.addWidget(self.grid_label)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.subtoolbar.addWidget(spacer)

    def customize_features(self):
        try:
            dialog = CustomizeFeaturesDialog(self)
            if dialog.exec_():
                grid_layout = dialog.grid_layout
                self.current_grid_layout = grid_layout
                self.grid_label.setText(grid_layout)
                existing_features = list(self.feature_instances.keys())
                self.display_features(existing_features, grid_layout)
            else:
                logging.info("Customize grid dialog cancelled")
        except Exception as e:
            logging.error(f"Error customizing grid: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error customizing grid: {str(e)}")

    def determine_grid_layout(self, num_features):
        if num_features <= 1:
            return "1x1"
        elif num_features == 2:
            return "1x2"
        elif num_features <= 4:
            return "2x2"
        elif num_features <= 6:
            return "2x3"
        else:
            return "3x3"

    def calculate_grid_sizes(self, grid_layout, console_height):
        rows, cols = map(int, grid_layout.split('x'))
        content_width = self.content_container.width() - 30
        content_height = self.content_container.height() - console_height - 20
        vertical_gap = 10  # Matches grid_layout.setSpacing(10)
        total_gaps_height = vertical_gap * (rows - 1) if rows > 1 else 0
        window_width = max(200, (content_width - (cols - 1) * 10 - 20) // cols)
        available_height = content_height - total_gaps_height
        window_height = max(150, available_height // rows)
        total_windows_height = (window_height * rows) + total_gaps_height
        return rows, cols, content_width, window_width, window_height, total_windows_height

    def display_features(self, feature_names, grid_layout):
        try:
            current_console_height = self.console.height()
            self.clear_content_layout()
            self.is_saving = False
            self.update_subtoolbar()

            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setStyleSheet("QScrollArea { background-color: #263238; border: none; }")
            scroll_widget = QWidget()
            self.grid_layout = QGridLayout()
            self.grid_layout.setContentsMargins(10, 10, 10, 10)
            self.grid_layout.setSpacing(10)
            scroll_widget.setLayout(self.grid_layout)
            scroll_area.setWidget(scroll_widget)
            self.content_layout.addWidget(scroll_area)
            self.scroll_area = scroll_area

            rows, cols, content_width, window_width, window_height, total_windows_height = self.calculate_grid_sizes(grid_layout, current_console_height)
            self.current_grid_layout = grid_layout
            self.grid_label.setText(grid_layout)

            scroll_widget.setMinimumSize(content_width, total_windows_height + 20)

            feature_classes = {
                "Create Tags": CreateTagsFeature,
                "Tabular View": TabularViewFeature,
                "Time View": TimeViewFeature,
                "Time Report": TimeReportFeature,
                "FFT": FFTViewFeature,
                "Waterfall": WaterfallFeature,
                "Orbit": OrbitFeature,
                "Trend View": TrendViewFeature,
                "Multiple Trend View": MultiTrendFeature,
                "Bode Plot": BodePlotFeature,
                "History Plot": HistoryPlotFeature,
                "Report": ReportFeature
            }

            # Clean up feature instances not in the new list
            features_to_remove = [name for name in self.feature_instances.keys() if name not in feature_names]
            for feature_name in features_to_remove:
                instance = self.feature_instances.pop(feature_name, None)
                if instance:
                    if hasattr(instance, 'cleanup'):
                        instance.cleanup()
                    widget = instance.get_widget()
                    if widget:
                        widget.hide()
                        widget.setParent(None)
                        widget.deleteLater()

            row = 0
            col = 0

            for feature_name in feature_names:
                if feature_name in feature_classes:
                    try:
                        feature_instance = self.feature_instances.get(feature_name)
                        if feature_instance:
                            try:
                                widget = feature_instance.get_widget()
                                if not widget or widget.isHidden():
                                    logging.warning(f"Feature instance {feature_name} exists but widget is invalid or hidden")
                                    del self.feature_instances[feature_name]
                                    feature_instance = None
                            except RuntimeError:
                                logging.warning(f"Feature instance {feature_name} is invalid, recreating")
                                del self.feature_instances[feature_name]
                                feature_instance = None

                        if not feature_instance or getattr(feature_instance, 'project_name', None) != self.current_project:
                            if not self.db.is_connected():
                                self.db.reconnect()
                            logging.info(f"Creating new instance for feature: {feature_name}")
                            feature_instance = feature_classes[feature_name](self, self.db, self.current_project)
                            self.feature_instances[feature_name] = feature_instance

                        window = FeatureWindow(feature_instance, feature_name, self, window_width, window_height)
                        self.grid_layout.addWidget(window, row, col)
                        window.show()

                        col += 1
                        if col >= cols:
                            col = 0
                            row += 1
                    except Exception as e:
                        logging.error(f"Failed to create window for {feature_name}: {str(e)}")
                        QMessageBox.warning(self, "Error", f"Failed to create window for {feature_name}: {str(e)}")
                else:
                    logging.warning(f"Unknown feature: {feature_name}")

            # Fill empty cells
            while row < rows:
                while col < cols:
                    empty_widget = QWidget()
                    empty_widget.setStyleSheet("background-color: transparent;")
                    empty_widget.setFixedSize(window_width, window_height)
                    self.grid_layout.addWidget(empty_widget, row, col)
                    empty_widget.show()
                    col += 1
                col = 0
                row += 1

            self.console.setFixedHeight(current_console_height)
            self.content_container.update()
            self.resize_grid()

            logging.info(f"Initialized {grid_layout} grid with {len(feature_names)} features")
        except Exception as e:
            logging.error(f"Error displaying features: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error displaying features: {str(e)}")

    def resize_grid(self):
        try:
            if not self.current_grid_layout or not self.grid_layout:
                return

            rows, cols, content_width, window_width, window_height, total_windows_height = self.calculate_grid_sizes(self.current_grid_layout, self.console.height())

            for row in range(rows):
                for col in range(cols):
                    item = self.grid_layout.itemAtPosition(row, col)
                    if item and item.widget():
                        widget = item.widget()
                        if isinstance(widget, FeatureWindow):
                            widget.normal_size = QSize(window_width, window_height)
                            widget.minimized_size = QSize(window_width, 30)
                            widget.maximized_size = QSize(content_width - 20, self.content_container.height() - self.console.height() - 20)

                            if not widget.is_maximized:
                                widget.setFixedSize(widget.normal_size if not widget.is_minimized else widget.minimized_size)
                            widget.show()
                        else:
                            widget.setFixedSize(window_width, window_height)
                            widget.show()

            if self.scroll_area and self.scroll_area.widget():
                self.scroll_area.widget().setMinimumSize(content_width, total_windows_height + 20)

            self.content_container.update()
            logging.info(f"Resized {self.current_grid_layout} grid windows to {window_width}x{window_height}")
        except Exception as e:
            logging.error(f"Error resizing grid: {str(e)}")

    def load_project_features(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            self.tree.clear()
            self.add_project_to_tree(self.current_project)

            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                if item.text(0) == f"📁 {self.current_project}":
                    item.setExpanded(True)
                    self.tree.setCurrentItem(item)
                    self.tree.scrollToItem(item)
                    break
        except Exception as e:
            logging.error(f"Failed to load project features: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to load project features: {str(e)}")

    def add_project_to_tree(self, project_name):
        project_item = QTreeWidgetItem(self.tree)
        project_item.setText(0, f"📁 {project_name}")
        project_item.setData(0, Qt.UserRole, {"type": "project", "name": project_name})

        features = [
            ("Create Tags", "🏷️ Create Tags", "Add Create Tags Feature"),
            ("Time View", "⏱️ Time View", "Add Time View Feature"),
            ("Tabular View", "📋 Tabular View", "Add Tabular View Feature"),
            ("FFT", "📈 FFT", "Add FFT View Feature"),
            ("Waterfall", "🌊 Waterfall", "Add Waterfall Feature"),
            ("Orbit", "🪐 Orbit", "Add Orbit Feature"),
            ("Trend View", "📉 Trend View", "Add Trend View Feature"),
            ("Multiple Trend View", "📊 Multiple Trend View", "Add Multiple Trend View Feature"),
            ("Bode Plot", "🔍 Bode Plot", "Add Bode Plot Feature"),
            ("History Plot", "🕰️ History Plot", "Add History Plot Feature"),
            ("Time Report", "📄 Time Report", "Add Time Report Feature"),
            ("Report", "📝 Report", "Add Report Feature")
        ]

        for feature, text_icon, tooltip in features:
            feature_item = QTreeWidgetItem(project_item)
            feature_item.setText(0, text_icon)
            feature_item.setToolTip(0, tooltip)
            feature_item.setData(0, Qt.UserRole, {"type": "feature", "name": feature, "project": project_name})

    def on_tree_item_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        try:
            logging.info(f"Tree item clicked: {data}")

            if data["type"] == "project":
                self.current_feature = None
                self.is_saving = False
                self.feature_instances.clear()
                self.display_features(["Create Tags"], "1x1")
            elif data["type"] == "feature":
                feature_name = data["name"]
                if feature_name in self.feature_instances:
                    for i in range(self.grid_layout.count()):
                        grid_item = self.grid_layout.itemAt(i)
                        if grid_item and grid_item.widget():
                            widget = grid_item.widget()
                            if isinstance(widget, FeatureWindow) and widget.feature_name == feature_name:
                                widget.raise_()
                                widget.activateWindow()
                                logging.info(f"Feature {feature_name} already in grid, brought to focus")
                                return
                self.add_feature_to_grid(feature_name)
        except Exception as e:
            logging.error(f"Error handling tree item click: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error handling tree item click: {str(e)}")

    def add_feature_to_grid(self, feature_name):
        try:
            logging.info(f"Adding feature to grid: {feature_name}")

            feature_classes = {
                "Create Tags": CreateTagsFeature,
                "Tabular View": TabularViewFeature,
                "Time View": TimeViewFeature,
                "Time Report": TimeReportFeature,
                "FFT": FFTViewFeature,
                "Waterfall": WaterfallFeature,
                "Orbit": OrbitFeature,
                "Trend View": TrendViewFeature,
                "Multiple Trend View": MultiTrendFeature,
                "Bode Plot": BodePlotFeature,
                "History Plot": HistoryPlotFeature,
                "Report": ReportFeature
            }

            if feature_name not in feature_classes:
                logging.warning(f"Unknown feature: {feature_name}")
                QMessageBox.warning(self, "Error", f"Unknown feature: {feature_name}")
                return

            if feature_name in self.feature_instances:
                QMessageBox.information(self, "Info", f"Feature '{feature_name}' is already displayed in the grid.")
                for i in range(self.grid_layout.count()):
                    item = self.grid_layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        if isinstance(widget, FeatureWindow) and widget.feature_name == feature_name:
                            widget.raise_()
                            widget.activateWindow()
                            logging.info(f"Feature {feature_name} already in grid, brought to focus")
                            return
                return

            existing_features = list(self.feature_instances.keys())
            existing_features.append(feature_name)
            num_features = len(existing_features)
            new_grid_layout = self.determine_grid_layout(num_features)
            self.display_features(existing_features, new_grid_layout)
            self.update_subtoolbar()

            logging.info(f"Added feature {feature_name}, new grid layout: {new_grid_layout}")
        except Exception as e:
            logging.error(f"Error adding feature to grid: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error adding feature to grid: {str(e)}")

    def open_project(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            projects = self.db.load_projects()

            if not projects:
                QMessageBox.warning(self, "Error", "No projects available to open!")
                return

            project_name, ok = QInputDialog.getItem(self, "Open Project", "Select project:", projects, 0, False)

            if ok and project_name:
                if project_name in self.project_selection_window.open_dashboards:
                    self.project_selection_window.open_dashboards[project_name].raise_()
                    self.project_selection_window.open_dashboards[project_name].activateWindow()
                    return

                dashboard = DashboardWindow(self.db, self.email, project_name, self.project_selection_window)
                dashboard.show()
                self.project_selection_window.open_dashboards[project_name] = dashboard
                self.project_selection_window.load_projects()
                QMessageBox.information(self, "Success", f"Opened project: {project_name}")
                self.update_file_bar()
        except Exception as e:
            logging.error(f"Error opening project: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error opening project: {str(e)}")

    def create_project(self):
        project_name, ok = QInputDialog.getText(self, "Create Project", "Enter project name:")

        if ok and project_name:
            try:
                if not self.db.is_connected():
                    self.db.reconnect()

                success, message = self.db.create_project(project_name)

                if success:
                    dashboard = DashboardWindow(self.db, self.email, project_name, self.project_selection_window)
                    dashboard.show()
                    self.project_selection_window.open_dashboards[project_name] = dashboard
                    self.project_selection_window.load_projects()
                    self.update_subtoolbar()
                    QMessageBox.information(self, "Success", message)
                    self.update_file_bar()
                else:
                    QMessageBox.warning(self, "Error", message)
            except Exception as e:
                logging.error(f"Error creating project: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error creating project: {str(e)}")

    def edit_project_dialog(self):
        old_project_name = self.current_project
        new_project_name, ok = QInputDialog.getText(self, "Edit Project", "Enter new project name:", text=old_project_name)

        if not ok or not new_project_name or new_project_name == old_project_name:
            return

        try:
            if not self.db.is_connected():
                self.db.reconnect()

            success, message = self.db.edit_project(old_project_name, new_project_name)

            if success:
                self.current_project = new_project_name
                self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
                self.load_project_features()
                self.setup_mqtt()
                self.update_toolbar()
                self.update_subtoolbar()

                existing_features = list(self.feature_instances.keys())
                self.display_features(existing_features, self.current_grid_layout)

                if old_project_name in self.project_selection_window.open_dashboards:
                    self.project_selection_window.open_dashboards[new_project_name] = self.project_selection_window.open_dashboards.pop(old_project_name)

                self.project_selection_window.load_projects()
                QMessageBox.information(self, "Success", message)
                self.update_file_bar()
            else:
                QMessageBox.warning(self, "Error", message)
        except Exception as e:
            logging.error(f"Error editing project: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error editing project: {str(e)}")

    def delete_project(self):
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {self.current_project}?",
                                     QMessageBox.Yes | QDialogButtonBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                if not self.db.is_connected():
                    self.db.reconnect()

                success, message = self.db.delete_project(self.current_project)

                if success:
                    if self.current_project in self.project_selection_window.open_dashboards:
                        del self.project_selection_window.open_dashboards[self.current_project]

                    self.project_selection_window.load_projects()
                    self.close()
                    QMessageBox.information(self, "Success", message)
                else:
                    QMessageBox.warning(self, "Error", message)
            except Exception as e:
                logging.error(f"Error deleting project: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error deleting project: {str(e)}")

    def start_saving(self):
        if "Time View" not in self.feature_instances:
            QMessageBox.warning(self, "Error", "Time View feature is not active in the grid!")
            return

        feature_instance = self.feature_instances.get("Time View")

        if not feature_instance:
            QMessageBox.warning(self, "Error", "Time View feature not initialized!")
            return

        try:
            feature_instance.start_saving()
            self.is_saving = True
            self.update_subtoolbar()
            logging.info("Started saving data from dashboard")
            self.update_file_bar()
        except Exception as e:
            logging.error(f"Failed to start saving: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to start saving: {str(e)}")

    def stop_saving(self):
        if "Time View" not in self.feature_instances:
            QMessageBox.warning(self, "Error", "Time View feature is not active in the grid!")
            return

        feature_instance = self.feature_instances.get("Time View")

        if not feature_instance:
            QMessageBox.warning(self, "Error", "Time View feature not initialized!")
            return

        try:
            feature_instance.stop_saving()
            self.is_saving = False
            self.update_subtoolbar()
            logging.info("Stopped saving data from dashboard")
            self.update_file_bar()
        except Exception as e:
            logging.error(f"Failed to stop saving: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to stop saving: {str(e)}")

    def display_dashboard(self):
        self.current_feature = None
        self.is_saving = False
        self.timer.stop()
        self.feature_instances.clear()
        self.display_features(["Create Tags"], "1x1")
        self.update_file_bar()

    def clear_content_layout(self):
        try:
            while self.content_layout.count():
                item = self.content_layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    widget.hide()
                    widget.setParent(None)
                    widget.deleteLater()

            for child in self.content_container.findChildren(QWidget):
                if child != self.console:
                    child.hide()
                    child.setParent(None)
                    child.deleteLater()

            for feature_name, instance in list(self.feature_instances.items()):
                try:
                    if hasattr(instance, 'cleanup'):
                        instance.cleanup()
                    widget = instance.get_widget()
                    if widget:
                        widget.hide()
                        widget.setParent(None)
                        widget.deleteLater()
                except Exception as e:
                    logging.error(f"Error cleaning up feature {feature_name}: {str(e)}")
                finally:
                    del self.feature_instances[feature_name]

            self.grid_layout = None
            self.scroll_area = None
            self.content_container.update()
            gc.collect()

            logging.info("Content layout cleared")
        except Exception as e:
            logging.error(f"Error clearing content layout: {str(e)}")

    def settings_action(self):
        QMessageBox.information(self, "Settings", "Settings functionality not implemented yet.")
        self.update_file_bar()

    def refresh_action(self):
        try:
            existing_features = list(self.feature_instances.keys())
            self.display_features(existing_features, self.current_grid_layout)
            QMessageBox.information(self, "Refresh", "Refreshed current view!")
            self.update_file_bar()
        except Exception as e:
            logging.error(f"Error refreshing view: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error refreshing view: {str(e)}")

    def closeEvent(self, event):
        try:
            if self.timer.isActive():
                self.timer.stop()
            self.cleanup_mqtt()
            self.clear_content_layout()

            if self.db and self.db.is_connected():
                self.db.close_connection()

            if self.current_project in self.project_selection_window.open_dashboards:
                del self.project_selection_window.open_dashboards[self.current_project]

            app = QApplication.instance()
            if app:
                app.quit()
        except Exception as e:
            logging.error(f"Error during closeEvent: {str(e)}")
        finally:
            event.accept()