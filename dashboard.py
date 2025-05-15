import sys
import gc
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSplitter,
                             QToolBar, QAction, QTreeWidget, QTreeWidgetItem, QInputDialog, QMessageBox,
                             QSizePolicy, QApplication, QTextEdit, QMdiArea, QMdiSubWindow)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon, QColor
import os
from mqtthandler import MQTTHandler  # Assumes QThread-based MQTTHandler
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
import logging
import uuid

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
        self.sub_windows = {}  # Track sub-windows for each feature
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.is_saving = False
        self.mqtt_connected = False
        self.fft_window = None  # Kept for compatibility, not used
        self.current_layout = (2, 2)  # Default layout: 2x2 (rows, cols)

        # Initialize UI first
        self.initUI()

        # Defer other initialization tasks to ensure smooth window opening
        QTimer.singleShot(0, self.deferred_initialization)

    def deferred_initialization(self):
        """Perform initialization tasks after the window is shown."""
        self.load_project_features()
        self.setup_mqtt()
        self.display_feature_content("Create Tags", self.current_project)

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
        self.update_mqtt_status_indicator()

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
            self.update_mqtt_status_indicator()
            logging.info(f"MQTT connected for project: {self.current_project}")
            self.append_to_console(f"MQTT connected for project: {self.current_project}")
        except Exception as e:
            logging.error(f"Failed to connect MQTT: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to connect MQTT: {str(e)}")
            self.append_to_console(f"Failed to connect MQTT: {str(e)}")
            self.mqtt_connected = False
            self.update_mqtt_status_indicator()

    def disconnect_mqtt(self):
        """Disconnect from MQTT."""
        if not self.mqtt_connected:
            self.append_to_console("Already disconnected from MQTT")
            return
        try:
            self.cleanup_mqtt()
            self.update_subtoolbar()
            self.update_mqtt_status_indicator()
            logging.info(f"MQTT disconnected for project: {self.current_project}")
            self.append_to_console(f"MQTT disconnected for project: {self.current_project}")
        except Exception as e:
            logging.error(f"Failed to disconnect MQTT: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to disconnect MQTT: {str(e)}")
            self.append_to_console(f"Failed to disconnect MQTT: {str(e)}")
            self.update_mqtt_status_indicator()

    def on_data_received(self, tag_name, values):
        """Handle incoming MQTT data."""
        if self.current_feature and self.current_project:
            feature_instance = self.feature_instances.get(self.current_feature)
            if feature_instance and hasattr(feature_instance, 'on_data_received'):
                try:
                    feature_instance.on_data_received(tag_name, values)
                except Exception as e:
                    logging.error(f"Error in on_data_received for {self.current_feature}: {str(e)}")

    def on_mqtt_status(self, message):
        """Handle MQTT connection status updates."""
        self.mqtt_connected = "Connected" in message
        self.append_to_console(f"MQTT Status: {message}")
        self.update_mqtt_status_indicator()
        self.update_subtoolbar()

    def append_to_console(self, text):
        """Append MQTT-related text to the console widget when maximized."""
        if "MQTT" in text or "mqtt" in text or "layout" in text.lower():
            logging.info(text)  # Always log messages
            if hasattr(self, 'console_message_area') and self.console_message_area.isVisible():
                self.console_message_area.append(text)
                self.console_message_area.ensureCursorVisible()

    def update_mqtt_status_indicator(self):
        """Update the MQTT connection status indicator at the bottom of the console."""
        if hasattr(self, 'mqtt_status_label'):
            status_icon = "🟢" if self.mqtt_connected else "🔴"
            self.mqtt_status_label.setText(f"MQTT Connection status {status_icon}")
            self.mqtt_status_label.setStyleSheet("""
                QLabel {
                    background-color: black;
                    color: #FFFFFF;
                    font-size: 14px;
                    font:bold;
                    padding: 2px 8px;
                    border-radius: 0px;
                }
            """)

    def initUI(self):
        """Initialize the UI with a full-width console, MQTT status at bottom with red background."""
        self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
        self.setWindowState(Qt.WindowMaximized)

        # Apply global stylesheet
        app = QApplication.instance()
        app.setStyleSheet("""
            QInputDialog, QMessageBox {
                background-color: #1e2937;
                color: white;
                font-size: 16px;
                border: 1px solid #2c3e50;
                border-radius: 8px;
                padding: 15px;
                width:500px;
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
                transition: background-color 0.2s ease;
            }
            QInputDialog QPushButton:hover,
            QMessageBox QPushButton:hover {
                background-color: #357abd;
            }
            QInputDialog QPushButton:pressed,
            QMessageBox QPushButton:pressed {
                background-color: #2c5d9b;
            }
            QMdiSubWindow {
                background-color: #263238;
                border: 1px solid #4a90e2;
                border-radius: 4px;
            }
            QMdiSubWindow > QWidget {
                background-color: #263238;
                color: #ecf0f1;
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

        # Feature toolbar
        self.toolbar = QToolBar("Features")
        self.toolbar.setFixedHeight(75)
        self.update_toolbar()
        main_layout.addWidget(self.toolbar)

        # Main splitter for tree and MDI area
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setContentsMargins(0, 0, 0, 0)
        main_splitter.setHandleWidth(1)
        main_splitter.setStyleSheet("QSplitter::handle { background-color: #2c3e50; }")
        main_layout.addWidget(main_splitter)

        # Tree widget
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

        # Right container for MDI area and subtoolbar
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
        self.current_feature_label = QLabel("")
        self.current_feature_label.setStyleSheet("color: #333; font-size: 16px; font-weight: bold;")
        subtoolbar_layout.addWidget(self.subtoolbar)
        self.update_subtoolbar()
        right_layout.addWidget(subtoolbar_container)

        # MDI area
        self.mdi_area = QMdiArea()
        self.mdi_area.setStyleSheet("QMdiArea { background-color: #263238; border: none; }")
        # self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_layout.addWidget(self.mdi_area, 1)

        main_splitter.addWidget(right_container)
        main_splitter.setSizes([250, 950])

        # Console container (full width)
        self.console_container = QWidget()
        self.console_layout = QVBoxLayout()
        self.console_layout.setContentsMargins(0, 0, 0, 0)
        self.console_layout.setSpacing(0)
        self.console_container.setLayout(self.console_layout)

        # Button container for console controls
        self.button_container = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 0, 5, 0)
        button_layout.setSpacing(5)
        self.button_container.setLayout(button_layout)

        # Spacer to push buttons to the right for layout icon
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        button_layout.addWidget(spacer)

        # Clear console button
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

        # Minimize console button
        minimize_button = QPushButton("-")
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

        # Maximize console button
        maximize_button = QPushButton("🗖")
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

        # Console message area (hidden when minimized)
        self.console_message_area = QTextEdit()
        self.console_message_area.setReadOnly(True)
        self.console_message_area.setFixedHeight(0)  # Hidden initially
        self.console_message_area.setStyleSheet("""
            QTextEdit { 
                background-color: #212121; 
                color: #e0e0e0; 
                border: none; 
                font-family: Consolas, monospace; 
                font-size: 14px; 
                padding: 10px; 
            }
        """)

        # Console header layout for MQTT status (full width, black background)
        self.console_header_container = QWidget()
        console_header_layout = QHBoxLayout()
        console_header_layout.setContentsMargins(0, 0, 0, 0)
        console_header_layout.setSpacing(0)
        self.console_header_container.setLayout(console_header_layout)

        # MQTT status indicator (full width)
        self.mqtt_status_label = QLabel("MQTT Connection 🔴")
        self.mqtt_status_label.setToolTip("MQTT Connection Status")
        self.mqtt_status_label.setStyleSheet("""
            QLabel {
                background-color: black;
                color: #FFFFFF;
                font-size: 14px;
                padding: 2px 8px;
                border-radius: 0px;
            }
        """)
        console_header_layout.addWidget(self.mqtt_status_label)

        # Initial layout (minimized state): buttons above status
        self.console_layout.addWidget(self.button_container)
        self.console_layout.addWidget(self.console_message_area)
        self.console_layout.addWidget(self.console_header_container)
        main_layout.addWidget(self.console_container, 0)  # Console spans full width at bottom

    def clear_console(self):
        """Clear the console output."""
        try:
            self.console_message_area.clear()
            logging.info("Console cleared")
        except Exception as e:
            logging.error(f"Error clearing console: {str(e)}")

    def minimize_console(self):
        """Minimize console to 50px, showing buttons above MQTT status."""
        try:
            # Hide message area
            self.console_message_area.setFixedHeight(0)
            self.console_message_area.hide()

            # Reorder layout: buttons above status
            self.console_layout.removeWidget(self.button_container)
            self.console_layout.removeWidget(self.console_message_area)
            self.console_layout.removeWidget(self.console_header_container)

            self.console_layout.addWidget(self.button_container)
            self.console_layout.addWidget(self.console_message_area)
            self.console_layout.addWidget(self.console_header_container)

            logging.info("Console minimized to 50px")
        except Exception as e:
            logging.error(f"Error minimizing console: {str(e)}")

    def maximize_console(self):
        """Maximize console to 150px, showing buttons above messages, status at bottom."""
        try:
            # Show message area
            self.console_message_area.setFixedHeight(100)  # Messages take 100px
            self.console_message_area.show()

            # Reorder layout: buttons, messages, status
            self.console_layout.removeWidget(self.button_container)
            self.console_layout.removeWidget(self.console_message_area)
            self.console_layout.removeWidget(self.console_header_container)

            self.console_layout.addWidget(self.button_container)
            self.console_layout.addWidget(self.console_message_area)
            self.console_layout.addWidget(self.console_header_container)

            logging.info("Console maximized to 100px")
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
                transition: background-color 0.3s ease; 
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
                        transition: background-color 0.3s ease; 
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
        """Update the subtoolbar with play/pause, MQTT controls, and right-aligned layout icon."""
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
                transition: background-color 0.3s ease; 
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
                        transition: background-color 0.3s ease; 
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

        # Add spacer to push layout icon to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.subtoolbar.addWidget(spacer)

        # Add layout icon (right-aligned)
        add_action(
            "🧮", "#ffffff",
            lambda: self.arrange_layout(prompt_for_layout=True),
            "Select and Arrange Sub-Windows in Grid Layout (1x2, 1x3, 2x2, 3x3)",
            True, "#90a4ae"
        )

    def arrange_layout(self, prompt_for_layout=False):
        """Arrange sub-windows in the current or user-selected grid layout, aligning to main section."""
        try:
            sub_windows = list(self.sub_windows.values())
            if not sub_windows:
                self.append_to_console("No sub-windows to arrange.")
                return

            if prompt_for_layout:
                layout_options = ["1x2", "2x2", "3x3"]
                layout_choice, ok = QInputDialog.getItem(self, "Select Layout",
                                                        "Choose a layout:",
                                                        layout_options, layout_options.index(f"{self.current_layout[0]}x{self.current_layout[1]}"), False)
                if not ok or not layout_choice:
                    self.append_to_console("Layout selection cancelled.")
                    return
                rows, cols = map(int, layout_choice.split('x'))
                self.current_layout = (rows, cols)
            else:
                rows, cols = self.current_layout

            GAP = 10
            num_windows = len(sub_windows)

            # Get MDI area dimensions
            mdi_rect = self.mdi_area.viewport().rect()
            mdi_width = mdi_rect.width()
            mdi_height = mdi_rect.height()

            if rows == 1 and cols == 2:
                # Special handling for 1x2 layout
                windows_per_grid = 2  # Each grid holds 2 windows side by side
                num_grids = (num_windows + 1) // 2  # Number of vertical stacks
                total_vertical_gaps = (num_grids - 1) * GAP if num_grids > 1 else 0
                window_width = max(700, (mdi_width) // 2)
                # Use half the viewport height per window to fit one pair visibly
                window_height = max(700, (mdi_height) // 2)

                # Calculate total content height for scrolling
                total_content_height = num_grids * (window_height + GAP) + total_vertical_gaps

                for i, sub_window in enumerate(sub_windows):
                    try:
                        grid_index = i // windows_per_grid  # Which vertical stack
                        col_in_grid = i % 2  # Left or right column

                        # Calculate position
                        x = col_in_grid * (window_width )
                        y = grid_index * (window_height)

                        sub_window.setGeometry(x, y, window_width, window_height)
                        sub_window.showNormal()
                        sub_window.raise_()
                    except Exception as e:
                        logging.error(f"Error arranging sub-window {i}: {str(e)}")
                        self.append_to_console(f"Error arranging sub-window {i}: {str(e)}")

                # Keep MDI area height fixed, enable scrolling
                self.mdi_area.setMinimumHeight(mdi_height)
                self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self.mdi_area.setMinimumSize(0, 0)  # Prevent forced stretching
                self.mdi_area.viewport().update()

            else:
                # Logic for other layouts (2x2, 1x3, 3x3)
                windows_per_grid = rows * cols
                num_grids = (num_windows + windows_per_grid - 1) // windows_per_grid
                horizontal_gaps_per_grid = (cols - 1) * GAP if cols > 1 else 0
                vertical_gaps_per_grid = (rows - 1) * GAP if rows > 1 else 0
                total_horizontal_gaps = horizontal_gaps_per_grid
                total_vertical_gaps = (num_grids - 1) * GAP if num_grids > 1 else 0
                total_vertical_gaps += vertical_gaps_per_grid * num_grids

                available_width = mdi_width - total_horizontal_gaps
                base_window_width = max(300, available_width // max(1, cols))
                base_window_height = max(200, (mdi_height - vertical_gaps_per_grid) // max(1, rows))

                for i, sub_window in enumerate(sub_windows):
                    try:
                        grid_index = i // windows_per_grid
                        index_in_grid = i % windows_per_grid
                        row_in_grid = index_in_grid // cols
                        col_in_grid = index_in_grid % cols

                        x = col_in_grid * (base_window_width + GAP)
                        y = (grid_index * (rows * base_window_height + vertical_gaps_per_grid + GAP)) + (row_in_grid * (base_window_height + GAP))
                        

                        window_width = base_window_width
                        window_height = base_window_height

                        if col_in_grid == cols - 1:
                            remaining_width = mdi_width - x - (cols - 1) * GAP
                            window_width = max(300, remaining_width)

                        if row_in_grid == rows - 1:
                            grid_top = grid_index * (rows * base_window_height + vertical_gaps_per_grid + GAP)
                            grid_height = (rows * base_window_height + (rows - 1) * GAP)
                            remaining_height = (mdi_height - grid_top - grid_height) // max(1, num_grids)
                            window_height = max(200, base_window_height + remaining_height // rows)

                        sub_window.setGeometry(x, y, window_width, window_height)
                        sub_window.showNormal()
                        sub_window.raise_()
                    except Exception as e:
                        logging.error(f"Error arranging sub-window {i}: {str(e)}")
                        self.append_to_console(f"Error arranging sub-window {i}: {str(e)}")

                total_height = num_grids * (rows * base_window_height + vertical_gaps_per_grid) + (num_grids - 1) * GAP
                self.mdi_area.setMinimumHeight(min(total_height, mdi_height))

            layout_str = f"{rows}x{cols}"
            logging.info(f"Arranged {num_windows} sub-windows in {layout_str} grid layout ({num_grids} grids) with 10px gaps")
            self.append_to_console(f"Arranged {num_windows} sub-windows in {layout_str} grid layout ({num_grids} grids) with 10px gaps")
        except Exception as e:
            logging.error(f"Error arranging layout: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error arranging layout: {str(e)}")
            self.append_to_console(f"Error arranging layout: {str(e)}")
            # Ensure MDI area allows scrolling
            total_height = num_grids * (rows * base_window_height + vertical_gaps_per_grid) + (num_grids - 1) * GAP
            self.mdi_area.setMinimumHeight(min(total_height, mdi_height))
            self.mdi_area.updateGeometry()
            self.mdi_area.viewport().update()

            layout_str = f"{rows}x{cols}"
            logging.info(f"Arranged {num_windows} sub-windows in {layout_str} grid layout ({num_grids} grids) with 10px gaps")
            self.append_to_console(f"Arranged {num_windows} sub-windows in {layout_str} grid layout ({num_grids} grids) with 10px gaps")
        except Exception as e:
            logging.error(f"Error arranging layout: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error arranging layout: {str(e)}")
            self.append_to_console(f"Error arranging layout: {str(e)}")

    def resizeEvent(self, event):
        """Handle window resize events to re-arrange sub-windows."""
        super().resizeEvent(event)
        QTimer.singleShot(50, lambda: self.arrange_layout(prompt_for_layout=False))

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
        """Add the current project and its features to the tree widget with text icons."""
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
                self.display_feature_content("Create Tags", self.current_project)
            elif data["type"] == "feature":
                self.current_feature = data["name"]
                self.is_saving = False
                self.display_feature_content(data["name"], self.current_project)
        except Exception as e:
            logging.error(f"Error handling tree item click: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error handling tree item click: {str(e)}")

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
                self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
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
        """Display the content for a selected feature in a QMdiSubWindow."""
        def render_feature():
            try:
                self.current_project = project_name
                self.current_feature = feature_name
                self.is_saving = False
                self.update_subtoolbar()
                self.current_feature_label.setText(feature_name)

                current_console_height = self.console_message_area.height()

                feature_instance = self.feature_instances.get(feature_name)
                sub_window = self.sub_windows.get(feature_name)

                if feature_instance and feature_instance.project_name == project_name and sub_window:
                    try:
                        if sub_window.isHidden():
                            sub_window.show()
                        sub_window.raise_()
                        sub_window.activateWindow()
                        self.arrange_layout(prompt_for_layout=False)
                        self.console_message_area.setFixedHeight(current_console_height)
                        return
                    except RuntimeError:
                        del self.feature_instances[feature_name]
                        del self.sub_windows[feature_name]
                        feature_instance = None
                        sub_window = None

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

                if feature_name in feature_classes:
                    try:
                        if not self.db.is_connected():
                            self.db.reconnect()
                        feature_instance = feature_classes[feature_name](self, self.db, project_name)
                        self.feature_instances[feature_name] = feature_instance
                        widget = feature_instance.get_widget()
                        if widget:
                            sub_window = QMdiSubWindow()
                            sub_window.setWidget(widget)
                            sub_window.setWindowTitle(feature_name)
                            sub_window.setAttribute(Qt.WA_DeleteOnClose)
                            sub_window.resize(400, 300)
                            self.mdi_area.addSubWindow(sub_window)
                            self.sub_windows[feature_name] = sub_window
                            sub_window.show()
                            sub_window.closeEvent = lambda event, fn=feature_name: self.on_subwindow_closed(event, fn)
                            self.arrange_layout(prompt_for_layout=False)
                            self.console_message_area.setFixedHeight(current_console_height)
                        else:
                            logging.error(f"Feature {feature_name} returned invalid widget")
                            QMessageBox.warning(self, "Error", f"Feature {feature_name} failed to initialize")
                    except Exception as e:
                        logging.error(f"Failed to load feature {feature_name}: {str(e)}")
                        QMessageBox.warning(self, "Error", f"Failed to load {feature_name}: {str(e)}")
                else:
                    logging.warning(f"Unknown feature: {feature_name}")
                    QMessageBox.warning(self, "Error", f"Unknown feature: {feature_name}")
            except Exception as e:
                logging.error(f"Error displaying feature content: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error displaying feature: {str(e)}")
            finally:
                self.console_message_area.setFixedHeight(current_console_height)

        QTimer.singleShot(50, render_feature)

    def on_subwindow_closed(self, event, feature_name):
        """Handle sub-window close event to clean up resources."""
        try:
            if feature_name in self.feature_instances:
                instance = self.feature_instances[feature_name]
                if hasattr(instance, 'cleanup'):
                    instance.cleanup()
                widget = instance.get_widget()
                if widget:
                    widget.hide()
                    widget.setParent(None)
                    widget.deleteLater()
                del self.feature_instances[feature_name]
            if feature_name in self.sub_windows:
                del self.sub_windows[feature_name]
            if self.current_feature == feature_name:
                self.current_feature = None
                self.is_saving = False
                self.current_feature_label.setText("")
                self.update_subtoolbar()
            self.arrange_layout(prompt_for_layout=False)
            self.mdi_area.setMinimumSize(0, 0)
            gc.collect()
        except Exception as e:
            logging.error(f"Error cleaning up sub-window for {feature_name}: {str(e)}")
        event.accept()

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
        self.update_subtoolbar()
        self.display_feature_content("Create Tags", self.current_project)
        self.update_file_bar()

    def clear_content_layout(self):
        """Clear all sub-windows and feature instances."""
        try:
            for feature_name in list(self.sub_windows.keys()):
                sub_window = self.sub_windows[feature_name]
                sub_window.close()
            self.sub_windows.clear()

            for feature_name in list(self.feature_instances.keys()):
                try:
                    instance = self.feature_instances[feature_name]
                    if hasattr(instance, 'cleanup'):
                        instance.cleanup()
                    widget = instance.get_widget()
                    if widget:
                        widget.hide()
                        widget.setParent(None)
                        widget.deleteLater()
                    del self.feature_instances[feature_name]
                except Exception as e:
                    logging.error(f"Error cleaning up feature instance {feature_name}: {str(e)}")

            self.mdi_area.setMinimumSize(0, 0)
            gc.collect()
        except Exception as e:
            logging.error(f"Error clearing content layout: {str(e)}")

    def settings_action(self):
        """Display greeting settings (not implemented)."""
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