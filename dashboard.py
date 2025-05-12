import sys
import gc
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSplitter,
                             QToolBar, QAction, QTreeWidget, QTreeWidgetItem, QInputDialog, QMessageBox,
                             QSizePolicy, QApplication, QTextEdit, QGridLayout, QDialog, QDialogButtonBox,
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

class FeatureCard(QWidget):
    """A card widget to display a feature with minimize, maximize, and cancel buttons."""
    def __init__(self, feature_instance, feature_name, parent=None, width=300, height=200):
        super().__init__(parent)
        self.feature_instance = feature_instance
        self.feature_name = feature_name
        self.is_minimized = False
        self.normal_size = QSize(width, height)  # Dynamic size based on grid
        self.minimized_size = QSize(width // 2, height // 2)  # Half normal size
        self.maximized_size = QSize(int(width * 1.5), int(height * 1.5))  # 1.5x normal size

        self.initUI()

    def initUI(self):
        """Initialize the card UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        self.setLayout(layout)

        # Header with feature name and control buttons
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        title_label = QLabel(self.feature_name)
        title_label.setStyleSheet("color: black; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        minimize_button = QPushButton("⏷")
        minimize_button.setToolTip("Minimize Card")
        minimize_button.clicked.connect(self.minimize_card)
        minimize_button.setStyleSheet("""
            QPushButton { 
                color: white; 
                font-size: 14px; 
                padding: 2px 6px; 
                border-radius: 3px; 
                background-color: #34495e; 
                border: none;
            }
            QPushButton:hover { background-color: #4a90e2; }
            QPushButton:pressed { background-color: #357abd; }
        """)
        header_layout.addWidget(minimize_button)

        maximize_button = QPushButton("⏶")
        maximize_button.setToolTip("Maximize Card")
        maximize_button.clicked.connect(self.maximize_card)
        maximize_button.setStyleSheet("""
            QPushButton { 
                color: white; 
                font-size: 14px; 
                padding: 2px 6px; 
                border-radius: 3px; 
                background-color: #34495e; 
                border: none;
            }
            QPushButton:hover { background-color: #4a90e2; }
            QPushButton:pressed { background-color: #357abd; }
        """)
        header_layout.addWidget(maximize_button)

        cancel_button = QPushButton("✖")
        cancel_button.setToolTip("Close Card")
        cancel_button.clicked.connect(self.close_card)
        cancel_button.setStyleSheet("""
            QPushButton { 
                color: white; 
                font-size: 14px; 
                padding: 2px 6px; 
                border-radius: 3px; 
                background-color: #d32f2f; 
                border: none;
            }
            QPushButton:hover { background-color: #ef5350; }
            QPushButton:pressed { background-color: #b71c1c; }
        """)
        header_layout.addWidget(cancel_button)

        layout.addLayout(header_layout)

        # Feature content
        self.content_widget = self.feature_instance.get_widget()
        if self.content_widget:
            layout.addWidget(self.content_widget)
        else:
            logging.error(f"No widget available for feature: {self.feature_name}")
            layout.addWidget(QLabel("Feature not available"))

        self.setStyleSheet("""
            QWidget { 
                background-color: #2c3e50; 
                border: 1px solid #34495e; 
                border-radius: 6px;
            }
        """)
        self.setFixedSize(self.normal_size)

    def minimize_card(self):
        """Minimize the card."""
        if not self.is_minimized:
            self.setFixedSize(self.minimized_size)
            self.is_minimized = True
            self.content_widget.hide()
            logging.info(f"Minimized card: {self.feature_name}")

    def maximize_card(self):
        """Maximize or restore the card."""
        if self.is_minimized:
            self.setFixedSize(self.normal_size)
            self.is_minimized = False
            self.content_widget.show()
            logging.info(f"Restored card: {self.feature_name}")
        else:
            self.setFixedSize(self.maximized_size)
            self.is_minimized = False
            self.content_widget.show()
            logging.info(f"Maximized card: {self.feature_name}")

    def close_card(self):
        """Close the card and clean up, triggering grid resize."""
        try:
            if self.feature_instance:
                if hasattr(self.feature_instance, 'cleanup'):
                    self.feature_instance.cleanup()
                self.content_widget.hide()
                self.content_widget.setParent(None)
                self.content_widget.deleteLater()
            self.hide()
            self.setParent(None)
            self.deleteLater()
            logging.info(f"Closed card: {self.feature_name}")
            # Remove feature instance and resize grid
            dashboard = self.parent()
            while dashboard and not isinstance(dashboard, DashboardWindow):
                dashboard = dashboard.parent()
            if dashboard:
                if self.feature_name in dashboard.feature_instances:
                    del dashboard.feature_instances[self.feature_name]
                if dashboard.current_grid_layout and dashboard.current_grid_layout != "1x1" and dashboard.card_layout:
                    dashboard.resize_grid()
        except Exception as e:
            logging.error(f"Error closing card {self.feature_name}: {str(e)}")

class CustomizeFeaturesDialog(QDialog):
    """Dialog to select grid layout only."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Customize Grid Layout")
        self.grid_layout = "1x1"
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Grid layout selection
        layout_label = QLabel("Select Grid Layout (Rows x Columns):")
        layout_label.setStyleSheet("color: #ecf0f1; font-size: 16px; padding-bottom: 5px;")
        layout.addWidget(layout_label)

        self.grid_combo = QComboBox()
        grid_options = ["1x1", "1x2", "2x1", "2x2", "2x3", "3x2", "3x3"]
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
        self.feature_instances = {}  # Cache feature instances
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.is_saving = False
        self.mqtt_connected = False
        self.fft_window = None  # Kept for compatibility
        self.card_layout = None  # For card-based feature display
        self.current_grid_layout = None  # Store current grid layout (e.g., "2x3")
        self.grid_label = ""  # Label for displaying grid layout

        # Initialize UI first
        self.initUI()

        # Defer other initialization tasks
        QTimer.singleShot(0, self.deferred_initialization)

    def deferred_initialization(self):
        """Perform initialization tasks after the window is shown."""
        try:
            self.load_project_features()
            self.setup_mqtt()
            self.display_feature_content("Create Tags", self.current_project)
        except Exception as e:
            logging.error(f"Error in deferred initialization: {str(e)}")
            QMessageBox.warning(self, "Error", f"Initialization error: {str(e)}")

    def setup_mqtt(self):
        """Set up MQTT handler for the current project if tags exist."""
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
        """Clean up existing MQTT handler."""
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
        """Retrieve tags for the current project from the database."""
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            tags = list(self.db.tags_collection.find({"project_name": self.current_project}))
            return [tag["tag_name"] for tag in tags]
        except Exception as e:
            logging.error(f"Failed to retrieve project tags: {str(e)}")
            return []

    def connect_mqtt(self):
        """Connect to MQTT based on project tags."""
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
        """Disconnect from MQTT."""
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
        """Handle incoming MQTT data."""
        if self.current_feature and self.current_project:
            feature_instance = self.feature_instances.get(self.current_feature)
            if feature_instance and hasattr(feature_instance, 'on_data_received'):
                try:
                    feature_instance.on_data_received(tag_name, values)
                except Exception as e:
                    logging.error(f"Error in on_data_received for {self.current_feature}: {str(e)}")
        # Update all card-based features
        for feature_name, instance in self.feature_instances.items():
            if hasattr(instance, 'on_data_received'):
                try:
                    instance.on_data_received(tag_name, values)
                except Exception as e:
                    logging.error(f"Error in on_data_received for card feature {feature_name}: {str(e)}")

    def on_mqtt_status(self, message):
        """Handle MQTT connection status updates."""
        self.mqtt_connected = "Connected" in message
        self.append_to_console(f"MQTT Status: {message}")
        self.update_subtoolbar()

    def append_to_console(self, text):
        """Append MQTT-related text to the console widget."""
        if "MQTT" in text or "mqtt" in text:
            if hasattr(self, 'console'):
                self.console.append(text)
                self.console.ensureCursorVisible()

    def initUI(self):
        """Initialize the user interface with a console fixed at the bottom."""
        self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
        self.setWindowState(Qt.WindowMaximized)

        # Apply global stylesheet
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
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

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
            ("Save", "Save Current Project Data", self.save_action),
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

        self.toolbar = QToolBar("Features")
        self.toolbar.setFixedHeight(75)
        self.update_toolbar()
        main_layout.addWidget(self.toolbar)

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setContentsMargins(0, 0, 0, 0)
        main_splitter.setHandleWidth(1)
        main_splitter.setStyleSheet("QSplitter::handle { background-color: #2c3e50; }")
        main_layout.addWidget(main_splitter)

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

        right_container = QWidget()
        right_container.setStyleSheet("background-color: #263238;")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_container.setLayout(right_layout)

        subtoolbar_container = QWidget()
        subtoolbar_container.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eceff1, stop:1 #cfd8dc);")
        subtoolbar_layout = QHBoxLayout()
        subtoolbar_layout.setContentsMargins(10, 0, 10, 0)
        subtoolbar_layout.setSpacing(10)
        subtoolbar_container.setLayout(subtoolbar_layout)

        self.subtoolbar = QToolBar("Controls")
        self.subtoolbar.setFixedHeight(100)
        self.current_feature_label = QLabel("")
        self.current_feature_label.setStyleSheet("color: #333; font-size: 16px; font-weight: bold;")
        subtoolbar_layout.addWidget(self.current_feature_label)
        subtoolbar_layout.addWidget(self.subtoolbar)
        self.update_subtoolbar()
        right_layout.addWidget(subtoolbar_container)

        self.content_container = QWidget()
        self.content_container.setStyleSheet("background-color: #263238;")
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_container.setLayout(self.content_layout)
        right_layout.addWidget(self.content_container, 1)

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
        """Clear the console output."""
        try:
            self.console.clear()
            logging.info("Console cleared")
        except Exception as e:
            logging.error(f"Error clearing console: {str(e)}")

    def minimize_console(self):
        """Set console height to 50px."""
        try:
            self.console.setFixedHeight(50)
            logging.info("Console minimized to 50px")
        except Exception as e:
            logging.error(f"Error minimizing console: {str(e)}")

    def maximize_console(self):
        """Set console height to 150px."""
        try:
            self.console.setFixedHeight(150)
            logging.info("Console maximized to 150px")
        except Exception as e:
            logging.error(f"Error maximizing console: {str(e)}")

    def update_file_bar(self):
        """Update the file bar stylesheet."""
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
        """Update the feature toolbar with text-based emoji icons."""
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
            action.triggered.connect(lambda: self.display_feature_content(feature_name, self.current_project))
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
            ("Create Tags", "🏷️", "#81c784", "Access Create Tags Feature"),
            ("Time View", "⏱️", "#ffb300", "Access Time View Feature"),
            ("Tabular View", "📋", "#64b5f6", "Access Tabular View Feature"),
            ("Time Report", "📄", "#4db6ac", "Access Time Report Feature"),
            ("FFT", "📈", "#ba68c8", "Access FFT View Feature"),
            ("Waterfall", "🌊", "#4dd0e1", "Access Waterfall Feature"),
            ("Orbit", "🪐", "#f06292", "Access Orbit Feature"),
            ("Trend View", "📉", "#aed581", "Access Trend View Feature"),
            ("Multiple Trend View", "📊", "#ff8a65", "Access Multiple Trend View Feature"),
            ("Bode Plot", "🔍", "#7986cb", "Access Bode Plot Feature"),
            ("History Plot", "🕰️", "#ef5350", "Access History Plot Feature"),
            ("Report", "📝", "#ab47bc", "Access Report Feature"),
        ]

        for feature_name, text_icon, color, tooltip in feature_actions:
            add_action(feature_name, text_icon, color, tooltip)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

    def update_subtoolbar(self):
        """Update the subtoolbar with controls and grid layout label."""
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

        is_time_view = self.current_feature == "Time View"
        add_action("▶", "#ffffff", self.start_saving, "Start Saving Data (Time View)", is_time_view and not self.is_saving, "#43a047")
        add_action("⏸", "#ffffff", self.stop_saving, "Stop Saving Data (Time View)", is_time_view and self.is_saving, "#ef5350")
        self.subtoolbar.addSeparator()

        connect_bg = "#43a047" if self.mqtt_connected else "#90a4ae"
        disconnect_bg = "#ef5350" if not self.mqtt_connected else "#90a4ae"
        add_action("🟢", "#ffffff", self.connect_mqtt, "Connect to MQTT", not self.mqtt_connected, connect_bg)
        add_action("🔴", "#ffffff", self.disconnect_mqtt, "Disconnect from MQTT", self.mqtt_connected, disconnect_bg)
        self.subtoolbar.addSeparator()

        # Add customize action with grid label
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

        # Grid layout label
        self.grid_label = QLabel(self.current_grid_layout or "")
        self.grid_label.setStyleSheet("color: #333; font-size: 14px; margin-left: 5px;")
        self.subtoolbar.addWidget(self.grid_label)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.subtoolbar.addWidget(spacer)

    def customize_features(self):
        """Open a dialog to select grid layout."""
        try:
            dialog = CustomizeFeaturesDialog(self)
            if dialog.exec_():
                grid_layout = dialog.grid_layout
                self.current_grid_layout = grid_layout
                self.grid_label.setText(grid_layout)
                if grid_layout == "1x1":
                    self.display_feature_content("Create Tags", self.current_project)
                else:
                    self.display_feature_cards([], grid_layout)
            else:
                logging.info("Customize grid dialog cancelled")
        except Exception as e:
            logging.error(f"Error customizing grid: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error customizing grid: {str(e)}")

    def display_feature_cards(self, feature_names, grid_layout):
        """Display an empty or partially filled grid for feature cards."""
        try:
            current_console_height = self.console.height()
            self.clear_content_layout()
            self.current_feature = None
            self.is_saving = False
            self.update_subtoolbar()

            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setStyleSheet("QScrollArea { background-color: #263238; border: none; }")
            scroll_widget = QWidget()
            self.card_layout = QGridLayout()
            self.card_layout.setContentsMargins(10, 10, 10, 10)
            self.card_layout.setSpacing(10)
            scroll_widget.setLayout(self.card_layout)
            scroll_area.setWidget(scroll_widget)
            self.content_layout.addWidget(scroll_area)

            rows, cols = map(int, grid_layout.split('x'))
            max_cards = rows * cols

            # Calculate card size with fallback
            content_width = self.content_container.width() if self.content_container.width() > 100 else 950
            content_height = self.content_container.height() if self.content_container.height() > 100 else 600
            content_height -= current_console_height + 20
            card_width = max(200, (content_width - (cols - 1) * 10 - 20) // cols)
            card_height = max(150, (content_height - (rows - 1) * 10) // rows)

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

            row = 0
            col = 0
            for feature_name in feature_names[:max_cards]:
                if feature_name in feature_classes:
                    try:
                        feature_instance = self.feature_instances.get(feature_name)
                        if not feature_instance or getattr(feature_instance, 'project_name', None) != self.current_project:
                            if not self.db.is_connected():
                                self.db.reconnect()
                            feature_instance = feature_classes[feature_name](self, self.db, self.current_project)
                            self.feature_instances[feature_name] = feature_instance

                        card = FeatureCard(feature_instance, feature_name, self, card_width, card_height)
                        self.card_layout.addWidget(card, row, col)

                        col += 1
                        if col >= cols:
                            col = 0
                            row += 1
                    except Exception as e:
                        logging.error(f"Failed to create card for {feature_name}: {str(e)}")
                        QMessageBox.warning(self, "Error", f"Failed to create card for {feature_name}: {str(e)}")
                else:
                    logging.warning(f"Unknown feature: {feature_name}")

            # Fill remaining grid with empty widgets
            while row < rows:
                while col < cols:
                    empty_widget = QWidget()
                    empty_widget.setStyleSheet("background-color: transparent;")
                    empty_widget.setFixedSize(card_width, card_height)
                    self.card_layout.addWidget(empty_widget, row, col)
                    col += 1
                col = 0
                row += 1

            self.console.setFixedHeight(current_console_height)
            logging.info(f"Initialized {grid_layout} grid with {len(feature_names)} features")
        except Exception as e:
            logging.error(f"Error displaying feature cards: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error displaying feature cards: {str(e)}")

    def resize_grid(self):
        """Resize all cards in the grid to fit the current window size."""
        try:
            if not self.current_grid_layout or not self.card_layout or self.current_grid_layout == "1x1":
                return

            rows, cols = map(int, self.current_grid_layout.split('x'))
            current_console_height = self.console.height()

            # Calculate card size with fallback
            content_width = self.content_container.width() if self.content_container.width() > 100 else 950
            content_height = self.content_container.height() if self.content_container.height() > 100 else 600
            content_height -= current_console_height + 20
            card_width = max(200, (content_width - (cols - 1) * 10 - 20) // cols)
            card_height = max(150, (content_height - (rows - 1) * 10) // rows)

            # Update all widgets in the grid
            for row in range(rows):
                for col in range(cols):
                    item = self.card_layout.itemAtPosition(row, col)
                    if item and item.widget():
                        widget = item.widget()
                        if isinstance(widget, FeatureCard):
                            widget.normal_size = QSize(card_width, card_height)
                            widget.minimized_size = QSize(card_width // 2, card_height // 2)
                            widget.maximized_size = QSize(int(card_width * 1.5), int(card_height * 1.5))
                            widget.setFixedSize(widget.normal_size if not widget.is_minimized else widget.minimized_size)
                        else:
                            widget.setFixedSize(card_width, card_height)

            logging.info(f"Resized {self.current_grid_layout} grid cards to {card_width}x{card_height}")
        except Exception as e:
            logging.error(f"Error resizing grid: {str(e)}")

    def load_project_features(self):
        """Load features for the current project into the tree."""
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
        """Add the current project and its features to the tree widget."""
        project_item = QTreeWidgetItem(self.tree)
        project_item.setText(0, f"📁 {project_name}")
        project_item.setData(0, Qt.UserRole, {"type": "project", "name": project_name})

        features = [
            ("Create Tags", "🏷️ Create Tags", "Access Create Tags Feature"),
            ("Time View", "⏱️ Time View", "Access Time View Feature"),
            ("Tabular View", "📋 Tabular View", "Access Tabular View Feature"),
            ("FFT", "📈 FFT", "Access FFT View Feature"),
            ("Waterfall", "🌊 Waterfall", "Access Waterfall Feature"),
            ("Orbit", "🪐 Orbit", "Access Orbit Feature"),
            ("Trend View", "📉 Trend View", "Access Trend View Feature"),
            ("Multiple Trend View", "📊 Multiple Trend View", "Access Multiple Trend View Feature"),
            ("Bode Plot", "🔍 Bode Plot", "Access Bode Plot Feature"),
            ("History Plot", "🕰️ History Plot", "Access History Plot Feature"),
            ("Time Report", "📄 Time Report", "Access Time Report Feature"),
            ("Report", "📝 Report", "Access Report Feature")
        ]

        for feature, text_icon, tooltip in features:
            feature_item = QTreeWidgetItem(project_item)
            feature_item.setText(0, text_icon)
            feature_item.setToolTip(0, tooltip)
            feature_item.setData(0, Qt.UserRole, {"type": "feature", "name": feature, "project": project_name})

    def on_tree_item_clicked(self, item, column):
        """Handle tree item clicks."""
        data = item.data(0, Qt.UserRole)
        try:
            if data["type"] == "project":
                self.current_feature = None
                self.is_saving = False
                self.current_grid_layout = None
                self.card_layout = None
                self.grid_label.setText("None")
                self.display_feature_content("Create Tags", self.current_project)
            elif data["type"] == "feature":
                feature_name = data["name"]
                if self.current_grid_layout and self.card_layout and self.current_grid_layout != "1x1":
                    existing_features = []
                    for i in range(self.card_layout.count()):
                        widget = self.card_layout.itemAt(i).widget()
                        if isinstance(widget, FeatureCard):
                            existing_features.append(widget.feature_name)
                    if feature_name in existing_features:
                        QMessageBox.information(self, "Info", f"Feature '{feature_name}' is already displayed in the grid.")
                        return

                    rows, cols = map(int, self.current_grid_layout.split('x'))
                    if len(existing_features) < rows * cols:
                        self.add_feature_to_grid(feature_name)
                    else:
                        QMessageBox.warning(self, "Error", "Grid is full! Choose a larger grid or remove a feature.")
                else:
                    self.current_feature = feature_name
                    self.is_saving = False
                    self.current_grid_layout = None
                    self.card_layout = None
                    self.grid_label.setText("None")
                    self.display_feature_content(feature_name, self.current_project)
        except Exception as e:
            logging.error(f"Error handling tree item click: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error handling tree item click: {str(e)}")

    def add_feature_to_grid(self, feature_name):
        """Add a single feature to the existing card layout."""
        try:
            if not self.current_grid_layout or not self.card_layout or self.current_grid_layout == "1x1":
                logging.warning("No active grid layout to add feature")
                self.display_feature_content(feature_name, self.current_project)
                return

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

            rows, cols = map(int, self.current_grid_layout.split('x'))
            # Calculate card size with fallback
            content_width = self.content_container.width() if self.content_container.width() > 100 else 950
            content_height = self.content_container.height() if self.content_container.height() > 100 else 600
            content_height -= self.console.height() + 20
            card_width = max(200, (content_width - (cols - 1) * 10 - 20) // cols)
            card_height = max(150, (content_height - (rows - 1) * 10) // rows)

            for row in range(rows):
                for col in range(cols):
                    item = self.card_layout.itemAtPosition(row, col)
                    if item and isinstance(item.widget(), QWidget) and item.widget().styleSheet() == "background-color: transparent;":
                        feature_instance = self.feature_instances.get(feature_name)
                        if not feature_instance or getattr(feature_instance, 'project_name', None) != self.current_project:
                            if not self.db.is_connected():
                                self.db.reconnect()
                            feature_instance = feature_classes[feature_name](self, self.db, self.current_project)
                            self.feature_instances[feature_name] = feature_instance

                        card = FeatureCard(feature_instance, feature_name, self, card_width, card_height)
                        item.widget().deleteLater()
                        self.card_layout.addWidget(card, row, col)
                        logging.info(f"Added feature {feature_name} to grid at position ({row}, {col})")
                        return
            QMessageBox.warning(self, "Error", "No empty space in the grid to add the feature!")
        except Exception as e:
            logging.error(f"Error adding feature to grid: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error adding feature to grid: {str(e)}")

    def open_project(self):
        """Open an existing project."""
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
        """Create a new project."""
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
        """Edit the current project's name."""
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
                self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project}')
                self.load_project_features()
                self.setup_mqtt()
                self.update_toolbar()
                self.update_subtoolbar()
                if self.current_feature:
                    self.display_feature_content(self.current_feature, self.current_project)
                else:
                    self.display_feature_content("Create Tags", self.current_project)
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
        """Delete the current project."""
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {self.current_project}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
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
        """Start saving data in Time View."""
        if self.current_feature != "Time View":
            QMessageBox.warning(self, "Error", "Saving is only available in Time View!")
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
        """Stop saving data in Time View."""
        if self.current_feature != "Time View":
            QMessageBox.warning(self, "Error", "Saving is only available in Time View!")
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

    def display_feature_content(self, feature_name, project_name):
        """Display the content for a selected feature within the main window."""
        def render_feature():
            try:
                self.current_project = project_name
                self.current_feature = feature_name
                self.is_saving = False
                self.update_subtoolbar()

                current_console_height = self.console.height()
                self.clear_content_layout()

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
                    logging.error(f"Unknown feature: {feature_name}")
                    QMessageBox.warning(self, "Error", f"Unknown feature: {feature_name}")
                    return

                feature_instance = self.feature_instances.get(feature_name)
                if not feature_instance or getattr(feature_instance, 'project_name', None) != project_name:
                    if not self.db.is_connected():
                        self.db.reconnect()
                    feature_instance = feature_classes[feature_name](self, self.db, project_name)
                    self.feature_instances[feature_name] = feature_instance

                widget = feature_instance.get_widget()
                if widget:
                    if feature_name in ["FFT", "Waterfall"]:
                        widget.setFixedSize(400, 400)
                        widget.move(50, 50)
                        widget.setParent(self.content_container)
                        widget.show()
                    else:
                        self.content_layout.addWidget(widget)
                        widget.show()
                else:
                    logging.error(f"Feature {feature_name} returned invalid widget")
                    QMessageBox.warning(self, "Error", f"Feature {feature_name} failed to initialize")

                self.console.setFixedHeight(current_console_height)
            except Exception as e:
                logging.error(f"Error displaying feature content: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error displaying feature: {str(e)}")

        QTimer.singleShot(50, render_feature)

    def save_action(self):
        """Save the current project's data."""
        if self.current_project:
            try:
                if not self.db.is_connected():
                    self.db.reconnect()
                project_data = self.db.get_project_data(self.current_project)
                if project_data:
                    QMessageBox.information(self, "Save", f"Data for project '{self.current_project}' saved successfully!")
                else:
                    QMessageBox.warning(self, "Save Error", "No data to save for the selected project!")
                self.update_file_bar()
            except Exception as e:
                logging.error(f"Error saving project: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error saving project: {str(e)}")
        else:
            QMessageBox.warning(self, "Save Error", "No project selected to save!")

    def refresh_action(self):
        """Refresh the current view."""
        try:
            if self.current_project and self.current_feature:
                self.display_feature_content(self.current_feature, self.current_project)
                QMessageBox.information(self, "Refresh", f"Refreshed view for '{self.current_feature}'!")
            else:
                self.display_feature_content("Create Tags", self.current_project)
                QMessageBox.information(self, "Refresh", "Refreshed default view!")
            self.update_file_bar()
        except Exception as e:
            logging.error(f"Error refreshing view: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error refreshing view: {str(e)}")

    def display_dashboard(self):
        """Display the default view for the project."""
        self.current_feature = None
        self.is_saving = False
        self.timer.stop()
        self.current_grid_layout = None
        self.card_layout = None
        self.grid_label.setText("None")
        self.display_feature_content("Create Tags", self.current_project)
        self.update_file_bar()

    def clear_content_layout(self):
        """Clear the content layout without affecting the console."""
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

            self.card_layout = None

            for feature_name in list(self.feature_instances.keys()):
                instance = self.feature_instances[feature_name]
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

            gc.collect()
            logging.info("Content layout cleared")
        except Exception as e:
            logging.error(f"Error clearing content layout: {str(e)}")

    def settings_action(self):
        """Display settings (not implemented)."""
        QMessageBox.information(self, "Settings", "Settings functionality not implemented yet.")
        self.update_file_bar()

    def closeEvent(self, event):
        """Handle window close event."""
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
