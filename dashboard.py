import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSplitter,
                             QToolBar, QAction, QTreeWidget, QTreeWidgetItem, QInputDialog, QMessageBox,
                             QSizePolicy, QApplication)
from PyQt5.QtCore import Qt, QSize, QTimer, QCoreApplication
from PyQt5.QtGui import QIcon
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

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
        self.is_saving = False  # Track saving state for Time View

        self.initUI()
        self.load_project_features()
        self.setup_mqtt()
        self.display_feature_content("Create Tags", self.current_project)

    def setup_mqtt(self):
        """Set up MQTT handler for the current project."""
        if not self.current_project:
            logging.warning("No project selected for MQTT setup")
            return
        if self.mqtt_handler:
            try:
                self.mqtt_handler.stop()
                self.mqtt_handler.deleteLater()
                logging.info("Previous MQTT handler stopped")
            except Exception as e:
                logging.error(f"Error stopping MQTT handler: {str(e)}")
            self.mqtt_handler = None
        try:
            self.mqtt_handler = MQTTHandler(self.db, self.current_project)
            self.mqtt_handler.data_received.connect(self.on_data_received)
            self.mqtt_handler.connection_status.connect(self.on_mqtt_status)
            self.mqtt_handler.start()
            logging.info(f"MQTT setup for project: {self.current_project}")
        except Exception as e:
            logging.error(f"Failed to setup MQTT: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to setup MQTT: {str(e)}")

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
        if self.current_feature == "Time View":
            feature_instance = self.feature_instances.get(self.current_feature)
            if feature_instance and hasattr(feature_instance, 'time_result'):
                try:
                    feature_instance.time_result.append(f"MQTT: {message}")
                except Exception as e:
                    logging.error(f"Error in on_mqtt_status: {str(e)}")

    def initUI(self):
        """Initialize the user interface."""
        self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
        self.showMaximized()

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.file_bar = QToolBar("File")
        self.file_bar.setStyleSheet("""
            QToolBar { background-color: #c3cb9b; border: none; padding: 5px; spacing: 10px; }
            QToolBar QToolButton { font-size: 20px; font-weight: bold; padding: 5px; }
            QToolBar QToolButton:hover { background-color: #lightblue; padding: 10px; }
        """)
        self.file_bar.setFixedHeight(40)
        self.file_bar.setMovable(False)
        self.file_bar.setFloatable(False)

        actions = [
            ("Home", self.display_dashboard),
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

        self.toolbar = QToolBar("Navigation")
        self.update_toolbar()
        main_layout.addWidget(self.toolbar)

        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel(f"PROJECT:{self.current_project.upper()}")
        self.tree.setStyleSheet("""
            QHeaderView::section {
                background-color: lightyellow;
                color: black;
                font-size: 20px;
                font: bold;
                text-align: center;
                padding: 2px;
            }
            QTreeWidget { background-color: #2c3e50; color: white; border: none; font-size: 20px; font: bold; }
            QTreeWidget::item { padding: 5px; text-align: center; font-size: 20px; }
            QTreeWidget::item:hover { background-color: #4a6077; }
            QTreeWidget::item:selected { background-color: #3498db; }
        """)
        header = self.tree.header()
        header.setDefaultAlignment(Qt.AlignCenter)
        self.tree.setFixedWidth(300)
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        main_splitter.addWidget(self.tree)

        content_container = QWidget()
        self.content_layout = QVBoxLayout()
        content_container.setLayout(self.content_layout)
        content_container.setStyleSheet("background-color: #34495e;")
        main_splitter.addWidget(content_container)
        main_splitter.setSizes([300, 900])
        main_splitter.setHandleWidth(0)

    def update_toolbar(self):
        """Update the navigation toolbar."""
        self.toolbar.clear()
        self.toolbar.setStyleSheet("""
            QToolBar { background-color: #83afa5; border: none; padding: 10px; spacing: 15px; margin: 0; }
            QToolBar::separator { width: 1px; margin: 0; }
            QToolButton { border: none; padding: 8px; border: 1px solid black; margin: 0; border-radius: 5px; background-color: #1e2937; }
            QToolButton:hover { background-color: #e0e0e0; }
            QToolButton:pressed { background-color: #d0d0d0; }
            QToolButton:focus { outline: none; border: 1px solid #0078d7; }
        """)
        self.toolbar.setIconSize(QSize(40, 40))
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)

        def add_action(text, icon_path, callback, tooltip=None):
            icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
            action = QAction(icon, text, self)
            action.triggered.connect(callback)
            if tooltip:
                action.setToolTip(tooltip)
            self.toolbar.addAction(action)

        add_action("New", "icons/new.png", self.create_project, "Create a New Project")
        add_action("", "icons/save.png", self.save_action, "Save Project")
        add_action("", "icons/refresh.png", self.refresh_action, "Refresh View")
        add_action("", "icons/edit.png", self.edit_project_dialog, "Edit Project Name")

        self.play_action = QAction(QIcon("icons/record.png"), "", self)
        self.play_action.triggered.connect(self.start_saving)
        self.play_action.setToolTip("Start Saving Data (Time View)")
        self.toolbar.addAction(self.play_action)

        self.pause_action = QAction(QIcon("icons/pause.png"), "", self)
        self.pause_action.triggered.connect(self.stop_saving)
        self.pause_action.setToolTip("Stop Saving Data (Time View)")
        self.toolbar.addAction(self.pause_action)

        is_time_view = self.current_feature == "Time View"
        self.play_action.setEnabled(is_time_view and not self.is_saving)
        self.pause_action.setEnabled(is_time_view and self.is_saving)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        add_action("Settings", "icons/settings.png", self.settings_action, "Settings")

    def load_project_features(self):
        """Load features for the current project into the tree."""
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            self.tree.clear()
            self.add_project_to_tree(self.current_project)
            # Expand the project item by default
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                if item.text(0) == self.current_project:
                    item.setExpanded(True)
                    self.tree.setCurrentItem(item)
                    self.tree.scrollToItem(item)
                    logging.debug(f"Loaded and expanded project: {self.current_project}")
                    break
            QCoreApplication.processEvents()
        except Exception as e:
            logging.error(f"Failed to load project features: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to load project features: {str(e)}")

    def add_project_to_tree(self, project_name):
        """Add the current project and its features to the tree widget."""
        project_item = QTreeWidgetItem(self.tree)
        project_item.setText(0, project_name)
        project_item.setIcon(0, QIcon("icons/folder.png") if os.path.exists("icons/folder.png") else QIcon())
        project_item.setData(0, Qt.UserRole, {"type": "project", "name": project_name})

        features = [
            ("Create Tags", "icons/tag.png"),
            ("Time View", "icons/time.png"),
            ("Tabular View", "icons/table.png"),
            ("FFT", "icons/fft.png"),
            ("Waterfall", "icons/waterfall.png"),
            ("Orbit", "icons/orbit.png"),
            ("Trend View", "icons/trend.png"),
            ("Multiple Trend View", "icons/multitrend.png"),
            ("Bode Plot", "icons/bode.png"),
            ("History Plot", "icons/history.png"),
            ("Time Report", "icons/report.png"),
            ("Report", "icons/report.png")
        ]

        for feature, icon_path in features:
            feature_item = QTreeWidgetItem(project_item)
            feature_item.setText(0, feature)
            feature_item.setIcon(0, QIcon(icon_path) if os.path.exists(icon_path) else QIcon())
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

    def create_project(self):
        """Create a new project."""
        project_name, ok = QInputDialog.getText(self, "Create Project", "Enter project name:")
        self.setStyleSheet("""
            QMessageBox, QInputDialog {
                background-color: #34495e;
                color: white;
                font-size: 14px;
                border-radius: 8px;
            }
            QMessageBox QLabel, QInputDialog QLabel {
                font-size: 16px;
                color: white;
                padding: 20px 20px;
            }
            QMessageBox QPushButton, QInputDialog QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                padding: 12px 20px;
                font-size: 14px;
                min-width: 250px;
            }
            QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {
                background-color: #2980b9;
            }
            QMessageBox QPushButton:pressed, QInputDialog QPushButton:pressed {
                background-color: #1abc9c;
            }
            QMessageBox QPushButton:focus, QInputDialog QPushButton:focus {
                border: none;
            }
        """)
        if ok and project_name:
            try:
                if not self.db.is_connected():
                    self.db.reconnect()
                success, message = self.db.create_project(project_name)
                if success:
                    # Open a new dashboard window for the new project
                    dashboard = DashboardWindow(self.db, self.email, project_name, self.project_selection_window)
                    dashboard.show()
                    self.project_selection_window.open_dashboards[project_name] = dashboard
                    self.project_selection_window.load_projects()  # Refresh project list
                    QMessageBox.information(self, "Success", message)
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
                self.tree.setHeaderLabel(self.current_project.upper())
                self.load_project_features()
                self.setup_mqtt()
                self.update_toolbar()
                if self.current_feature:
                    self.display_feature_content(self.current_feature, self.current_project)
                else:
                    self.display_feature_content("Create Tags", self.current_project)
                # Update the open_dashboards dictionary
                if old_project_name in self.project_selection_window.open_dashboards:
                    self.project_selection_window.open_dashboards[new_project_name] = self.project_selection_window.open_dashboards.pop(old_project_name)
                self.project_selection_window.load_projects()  # Refresh project list
                QMessageBox.information(self, "Success", message)
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
                    self.project_selection_window.load_projects()  # Refresh project list
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
            self.play_action.setEnabled(False)
            self.pause_action.setEnabled(True)
            logging.info("Started saving data from dashboard")
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
            self.play_action.setEnabled(True)
            self.pause_action.setEnabled(False)
            logging.info("Stopped saving data from dashboard")
        except Exception as e:
            logging.error(f"Failed to stop saving: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to stop saving: {str(e)}")

    def display_feature_content(self, feature_name, project_name):
        """Display the content for a selected feature."""
        logging.debug(f"Displaying feature: {feature_name} for project: {project_name}")
        self.current_project = project_name
        self.current_feature = feature_name
        self.is_saving = False
        self.update_toolbar()
        self.clear_content_layout()

        feature_instance = self.feature_instances.get(feature_name)
        if feature_instance and feature_instance.project_name == project_name:
            try:
                if feature_instance.get_widget().isVisible():
                    logging.debug(f"Reusing cached feature instance: {feature_name}")
                    self.content_layout.addWidget(feature_instance.get_widget())
                    if feature_name == "Time View":
                        self.play_action.setEnabled(not self.is_saving)
                        self.pause_action.setEnabled(self.is_saving)
                    return
            except RuntimeError:
                logging.debug(f"Invalid widget for {feature_name}, creating new instance")
                del self.feature_instances[feature_name]
                feature_instance = None

        feature_classes = {
            "Create Tags": CreateTagsFeature,
            "Tabular View": TabularViewFeature,
            "Time View": TimeViewFeature,
            # "FFT": FFTViewFeature,
            # "Waterfall": WaterfallFeature,
            # "Orbit": OrbitFeature,
            # "Trend View": TrendViewFeature,
            # "Multiple Trend View": MultiTrendFeature,
            # "Bode Plot": BodePlotFeature,
            # "History Plot": HistoryPlotFeature,
            "Time Report": TimeReportFeature,
            # "Report": ReportFeature
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
                    logging.debug(f"Created new feature instance: {feature_name}")
                    if feature_name == "Time View":
                        self.play_action.setEnabled(not self.is_saving)
                        self.pause_action.setEnabled(self.is_saving)
                else:
                    logging.error(f"Feature {feature_name} returned invalid widget")
                    QMessageBox.warning(self, "Error", f"Feature {feature_name} failed to initialize")
            except Exception as e:
                logging.error(f"Failed to load feature {feature_name}: {str(e)}")
                QMessageBox.warning(self, "Error", f"Failed to load {feature_name}: {str(e)}")
        else:
            logging.warning(f"Unknown feature: {feature_name}")
            QMessageBox.warning(self, "Error", f"Unknown feature: {feature_name}")

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
        except Exception as e:
            logging.error(f"Error refreshing view: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error refreshing view: {str(e)}")

    def display_dashboard(self):
        """Display the default view for the project."""
        self.current_feature = None
        self.is_saving = False
        self.timer.stop()
        self.update_toolbar()
        self.clear_content_layout()
        self.display_feature_content("Create Tags", self.current_project)

    def clear_content_layout(self):
        """Clear the content layout and clean up feature instances."""
        logging.debug("Clearing content layout")
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.hide()
                try:
                    widget.deleteLater()
                except Exception as e:
                    logging.error(f"Error deleting widget: {str(e)}")
        for feature_name in list(self.feature_instances.keys()):
            try:
                del self.feature_instances[feature_name]
            except Exception as e:
                logging.error(f"Error removing feature instance {feature_name}: {str(e)}")
        QCoreApplication.processEvents()

    def settings_action(self):
        """Display settings (not implemented)."""
        QMessageBox.information(self, "Settings", "Settings functionality not implemented yet.")

    def closeEvent(self, event):
        """Handle window close event."""
        self.timer.stop()
        if self.mqtt_handler:
            try:
                self.mqtt_handler.stop()
                self.mqtt_handler.deleteLater()
                logging.info("MQTT handler stopped on close")
            except Exception as e:
                logging.error(f"Error stopping MQTT handler on close: {str(e)}")
        self.clear_content_layout()
        try:
            if self.db.is_connected():
                self.db.close_connection()
        except Exception as e:
            logging.error(f"Error closing database connection: {str(e)}")
        # Remove this dashboard from open_dashboards
        if self.current_project in self.project_selection_window.open_dashboards:
            del self.project_selection_window.open_dashboards[self.current_project]
        event.accept()