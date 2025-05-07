import sys
import gc
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSplitter,
                             QToolBar, QAction, QTreeWidget, QTreeWidgetItem, QInputDialog, QMessageBox,
                             QSizePolicy, QApplication, QTextEdit)
from PyQt5.QtCore import Qt, QSize, QTimer, QCoreApplication
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
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.is_saving = False
        self.mqtt_connected = False

        self.initUI()
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

    def on_mqtt_status(self, message):
        """Handle MQTT connection status updates."""
        self.mqtt_connected = "Connected" in message
        self.append_to_console(f"MQTT Status: {message}")
        self.update_subtoolbar()

    def append_to_console(self, text):
        """Append MQTT-related text to the console widget."""
        if "MQTT" in text or "mqtt" in text:  # Only append MQTT-related messages
            if hasattr(self, 'console'):
                self.console.append(text)
                self.console.ensureCursorVisible()

    def initUI(self):
        """Initialize the user interface with a console."""
        self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
        self.showMaximized()

        # Apply global stylesheet for QInputDialog and QMessageBox
        app = QApplication.instance()
        app.setStyleSheet("""
    QInputDialog, QMessageBox {
        background-color: #2c3e50;
        color: white;
        font-size: 16px;
        width: 400px;
        border: 1px solid #1a252f;
        border-radius: 8px;
        padding: 15px;
    }

    QInputDialog QLineEdit {
        background-color: #34495e;
        color: white;
        border: 1px solid #3498db;
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
        background-color: #3498db;
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
        background-color: #2980b9;
    }

    QInputDialog QPushButton:pressed,
    QMessageBox QPushButton:pressed {
        background-color: #2471a3;
    }
""")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        self.file_bar = QToolBar("File")
        self.file_bar.setStyleSheet("""
            QToolBar {
                background-color: #eaeaea;
                border: none;
                padding: 0;
                spacing: 5px;
            }
            QToolBar QToolButton {
                font-size: 20px;
                font-weight: bold;
                color: black;
                padding: 8px 12px;
                border-radius: 4px;
                background-color: transparent;
            }
            QToolBar QToolButton:hover {
                background-color: #1976D2;
                color: white;
            }
        """)
        self.file_bar.setFixedHeight(40)
        self.file_bar.setMovable(False)
        self.file_bar.setFloatable(False)

        actions = [
            ("Home", self.display_dashboard),
            ("Open", self.open_project),
            ("New", self.create_project),
            ("Save", self.save_action),
            ("Settings", self.settings_action),
            ("Refresh", self.refresh_action),
            ("Exit", self.close)
        ]
        for text, func in actions:
            action = QAction(text, self)
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
        main_splitter.setStyleSheet("QSplitter::handle { background-color: #1e2937; }")
        main_layout.addWidget(main_splitter)

        self.tree = QTreeWidget()
        self.tree.header().hide()
        self.tree.setStyleSheet("""
            QTreeWidget { background-color: #1e2937; color: white; border: none; font-size: 16px; }
            QTreeWidget::item { padding: 8px; border-bottom: 1px solid #34495e; }
            QTreeWidget::item:hover { background-color: #34495e; }
            QTreeWidget::item:selected { background-color: #3498db; color: white; }
        """)
        self.tree.setFixedWidth(250)
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        main_splitter.addWidget(self.tree)

        right_container = QWidget()
        right_container.setStyleSheet("background-color: #2c3e50;")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_container.setLayout(right_layout)

        subtoolbar_container = QWidget()
        subtoolbar_container.setStyleSheet("background-color: #1e2937;")
        subtoolbar_layout = QVBoxLayout()
        subtoolbar_layout.setContentsMargins(0, 0, 0, 0)
        subtoolbar_layout.setSpacing(0)
        subtoolbar_container.setLayout(subtoolbar_layout)

        self.subtoolbar = QToolBar("Controls")
        self.subtoolbar.setFixedHeight(60)
        self.update_subtoolbar()
        subtoolbar_layout.addWidget(self.subtoolbar)

        content_container = QWidget()
        content_container.setStyleSheet("background-color: #2c3e50;")
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        content_container.setLayout(self.content_layout)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(200)
        self.console.setStyleSheet("""
            QTextEdit { background-color: black; color: white; border: none; font-family: Consolas, monospace; font-size: 14px; padding: 10px; }
        """)

        right_layout.addWidget(subtoolbar_container)
        right_layout.addWidget(content_container)
        right_layout.addWidget(self.console)

        main_splitter.addWidget(right_container)
        main_splitter.setSizes([250, 1000])

    def update_file_bar(self):
        """Force update and repaint the file bar to prevent glitching."""
        try:
            self.file_bar.setStyleSheet("""
                QToolBar {
                    background-color: #eaeaea;
                    border: none;
                    padding: 0;
                    spacing: 5px;
                }
                QToolBar QToolButton {
                    font-size: 20px;
                    font-weight: bold;
                    color: black;
                    padding: 8px 12px;
                    border-radius: 4px;
                    background-color: transparent;
                }
                QToolBar QToolButton:hover {
                    background-color: #1976D2;
                    color: white;
                }
            """)
            self.file_bar.hide()
            self.file_bar.show()
            self.file_bar.update()
            self.file_bar.repaint()
            QCoreApplication.processEvents()
        except Exception as e:
            logging.error(f"Error updating file bar: {str(e)}")

    def update_toolbar(self):
        """Update the feature toolbar with text-based icons."""
        self.toolbar.clear()
        self.toolbar.setStyleSheet("""
            QToolBar { background-color: #2c3e50; border: none; padding: 5px; spacing: 10px; }
            QToolButton { border: none; padding: 10px; border-radius: 6px; background-color: #34495e; font-size: 28px; color: white; }
            QToolButton:hover { background-color: #3498db; }
            QToolButton:pressed { background-color: #2980b9; }
            QToolButton:focus { outline: none; border: 1px solid #0078d7; }
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
                    QToolButton {{ color: {color}; font-size: 35px; border: none; border-radius: 6px; background-color: #34495e; }}
                    QToolButton:hover {{ background-color: #3498db; }}
                    QToolButton:pressed {{ background-color: #2980b9; }}
                """)

        feature_actions = [
            ("Create Tags", "🏷️", "#00cc00", "Access Create Tags Feature"),
            ("Time View", "⏱️", "#ff9900", "Access Time View Feature"),
            ("Tabular View", "📋", "#3399ff", "Access Tabular View Feature"),
            ("Time Report", "📄", "#33cc99", "Access Time Report Feature"),
            ("FFT", "📈", "#cc33ff", "Access FFT View Feature"),
            ("Waterfall", "🌊", "#00cccc", "Access Waterfall Feature"),
            ("Orbit", "🪐", "#ff66cc", "Access Orbit Feature"),
            ("Trend View", "📉", "#66cc00", "Access Trend View Feature"),
            ("Multiple Trend View", "📊", "#cc6600", "Access Multiple Trend View Feature"),
            ("Bode Plot", "🔍", "#6666ff", "Access Bode Plot Feature"),
            ("History Plot", "🕰️", "#ff3333", "Access History Plot Feature"),
            ("Report", "📝", "#9933cc", "Access Report Feature"),
        ]

        for feature_name, text_icon, color, tooltip in feature_actions:
            add_action(feature_name, text_icon, color, tooltip)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        self.toolbar.hide()
        self.toolbar.show()
        self.toolbar.update()
        self.toolbar.repaint()
        self.update_file_bar()

    def update_subtoolbar(self):
        """Update the subtoolbar with play/pause and MQTT controls."""
        self.subtoolbar.clear()
        self.subtoolbar.setStyleSheet("""
            QToolBar { background-color: #1e2937; border: none; padding: 5px; spacing: 10px; }
            QToolButton { border: none; padding: 8px; border-radius: 5px; background-color: #2c3e50; font-size: 24px; color: white; }
            QToolButton:hover { background-color: #3498db; }
            QToolButton:pressed { background-color: #2980b9; }
            QToolButton:focus { outline: none; border: 1px solid #0078d7; }
            QToolButton:disabled { background-color: #555555; color: #888888; }
        """)
        self.subtoolbar.setIconSize(QSize(25, 25))
        self.subtoolbar.setContentsMargins(10, 0, 10, 0)
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
                    QToolButton {{ color: {color}; font-size: 28px; border: none; padding: 8px; border-radius: 5px; background-color: {background_color}; }}
                    QToolButton:hover {{ background-color: #3498db; }}
                    QToolButton:pressed {{ background-color: #2980b9; }}
                    QToolButton:disabled {{ background-color: #555555; color: #888888; }}
                """)

        is_time_view = self.current_feature == "Time View"
        add_action("▶️", "#00ff00", self.start_saving, "Start Saving Data (Time View)", is_time_view and not self.is_saving, "#2c3e50")
        add_action("⏸️", "#ff3333", self.stop_saving, "Stop Saving Data (Time View)", is_time_view and self.is_saving, "#2c3e50")
        self.subtoolbar.addSeparator()
        
        connect_bg = "green" if self.mqtt_connected else "#2c3e50"
        disconnect_bg = "red" if not self.mqtt_connected else "#2c3e50"
        # add_action("🔗", "#ffffff", self.connect_mqtt, "Connect to MQTT", not self.mqtt_connected, connect_bg)
        # add_action("🔌", "#ffffff", self.disconnect_mqtt, "Disconnect from MQTT", self.mqtt_connected, disconnect_bg)
        add_action("🟢", "#ffffff", self.connect_mqtt, "Connect to MQTT", not self.mqtt_connected, connect_bg)
        add_action("🔴", "#ffffff", self.disconnect_mqtt, "Disconnect from MQTT", self.mqtt_connected, disconnect_bg)


        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.subtoolbar.addWidget(spacer)
        self.subtoolbar.hide()
        self.subtoolbar.show()
        self.subtoolbar.update()
        self.subtoolbar.repaint()
        QCoreApplication.processEvents()
        self.update_file_bar()

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
            QCoreApplication.processEvents()
            self.update_file_bar()
        except Exception as e:
            logging.error(f"Failed to load project features: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to load project features: {str(e)}")

    def add_project_to_tree(self, project_name):
        """Add the current project and its features to the tree widget with text icons."""
        project_item = QTreeWidgetItem(self.tree)
        project_item.setText(0, f"📁 {project_name}")
        project_item.setData(0, Qt.UserRole, {"type": "project", "name": project_name})

        features = [
            ("Create Tags", "🏷️"),
            ("Time View", "⏱️"),
            ("Tabular View", "📋"),
            ("FFT", "📈"),
            ("Waterfall", "🌊"),
            ("Orbit", "🪐"),
            ("Trend View", "📉"),
            ("Multiple Trend View", "📊"),
            ("Bode Plot", "🔍"),
            ("History Plot", "🕰️"),
            ("Time Report", "📄"),
            ("Report", "📝")
        ]

        for feature, text_icon in features:
            feature_item = QTreeWidgetItem(project_item)
            feature_item.setText(0, f"{text_icon} {feature}")
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
        """Display the content for a selected feature with delayed rendering."""
        def render_feature():
            try:
                self.current_project = project_name
                self.current_feature = feature_name
                self.is_saving = False
                self.update_subtoolbar()

                # Clear the layout and remove old widgets
                self.clear_content_layout()

                # Check if the feature instance already exists and is valid
                feature_instance = self.feature_instances.get(feature_name)
                if feature_instance and feature_instance.project_name == project_name:
                    try:
                        widget = feature_instance.get_widget()
                        if widget and not widget.isHidden():
                            self.content_layout.addWidget(widget)
                            widget.show()
                            self.update()
                            self.repaint()
                            QCoreApplication.processEvents()
                            self.update_file_bar()
                            return
                    except RuntimeError:
                        # Widget was deleted, remove the instance
                        del self.feature_instances[feature_name]
                        feature_instance = None

                # Define feature classes
                feature_classes = {
                    "Create Tags": CreateTagsFeature,
                    "Tabular View": TabularViewFeature,
                    "Time View": TimeViewFeature,
                    "Time Report": TimeReportFeature,
                #     "FFT": FFTViewFeature,
                #     "Waterfall": WaterfallFeature,
                #     "Orbit": OrbitFeature,
                #     "Trend View": TrendViewFeature,
                #     "Multiple Trend View": MultiTrendFeature,
                #     "Bode Plot": BodePlotFeature,
                #     "History Plot": HistoryPlotFeature,
                #     "Report": ReportFeature
                }

                if feature_name in feature_classes:
                    try:
                        if not self.db.is_connected():
                            self.db.reconnect()
                        feature_instance = feature_classes[feature_name](self, self.db, project_name)
                        self.feature_instances[feature_name] = feature_instance
                        widget = feature_instance.get_widget()
                        if widget:
                            self.content_layout.addWidget(widget)
                            widget.show()
                            self.update()
                            self.repaint()
                            QCoreApplication.processEvents()
                            self.update_file_bar()
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
                self.update()
                self.repaint()

        # Use a longer delay to allow UI to stabilize
        QTimer.singleShot(150, render_feature)

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
        """Clear the content layout without affecting the console."""
        try:
            # Hide and remove all widgets from the layout
            while self.content_layout.count():
                item = self.content_layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    widget.hide()
                    widget.setParent(None)
                    try:
                        widget.deleteLater()
                    except Exception as e:
                        logging.error(f"Error deleting widget: {str(e)}")

            # Clean up feature instances
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
            self.feature_instances.clear()

            # Force garbage collection to release memory
            gc.collect()

            # Force UI update
            QCoreApplication.processEvents()
            self.update()
            self.repaint()
            self.update_file_bar()
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
            QCoreApplication.processEvents()
            app = QApplication.instance()
            if app:
                app.quit()
        except Exception as e:
            logging.error(f"Error during closeEvent: {str(e)}")
        finally:
            event.accept()