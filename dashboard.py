import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSplitter,
                             QToolBar, QAction, QTreeWidget, QTreeWidgetItem, QInputDialog, QMessageBox,
                             QSizePolicy, QApplication)
from PyQt5.QtCore import Qt, QSize, QTimer, QCoreApplication
from PyQt5.QtGui import QIcon
import os
from mqtthandler import MQTTHandler  # Assumes the QThread-based MQTTHandler
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
    def __init__(self, db, email):
        super().__init__()
        self.db = db
        self.email = email
        self.current_project = None
        self.current_feature = None
        self.mqtt_handler = None
        self.feature_instances = {}  # Cache feature instances
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.is_saving = False  # Track saving state for Time View
        
        self.initUI()
        self.load_projects_async()

    def setup_mqtt(self):
        if self.current_project:
            if self.mqtt_handler:
                self.mqtt_handler.stop()
                self.mqtt_handler = None
            self.mqtt_handler = MQTTHandler(self.db, self.current_project)
            self.mqtt_handler.data_received.connect(self.on_data_received)
            self.mqtt_handler.connection_status.connect(self.on_mqtt_status)
            self.mqtt_handler.start()
            logging.info(f"MQTT setup for project: {self.current_project}")

    def on_data_received(self, tag_name, values):
        if self.current_feature and self.current_project:
            feature_instance = self.feature_instances.get(self.current_feature)
            if feature_instance and hasattr(feature_instance, 'on_data_received'):
                feature_instance.on_data_received(tag_name, values)

    def on_mqtt_status(self, message):
        if self.current_feature and self.current_feature == "Time View":
            feature_instance = self.feature_instances.get(self.current_feature)
            if feature_instance:
                feature_instance.time_result.append(f"MQTT: {message}")

    def initUI(self):
        self.setWindowTitle('Sarayu Desktop Application')
        self.showMaximized()

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.file_bar = QToolBar("File")
        self.file_bar.setStyleSheet("""
            QToolBar { background-color: #c3cb9b; border: none; padding: 5px; spacing: 10px; }
            QToolBar QToolButton { font-size: 20px; font-weight: bold; padding: 5px; }
            QToolBar QToolButton:hover { background-color: #lightblue;padding:10px }
        """)
        self.file_bar.setFixedHeight(40)
        self.file_bar.setMovable(False)
        self.file_bar.setFloatable(False)

        actions = [
            ("Home", self.display_dashboard),
            ("New", self.create_project),
            ("Open", self.open_project_dialog),
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
        self.tree.setHeaderLabel("Projects")
        self.tree.setStyleSheet("""
            QTreeWidget { background-color: #2c3e50; color: white; border: none;font-size:20px;font:bold}
            QTreeWidget::item { padding: 5px; text-align: center;font-size:20px }
            QTreeWidget::item:hover { background-color: #4a6077; }
            QTreeWidget::item:selected { background-color: #00000; }
        """)
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

        self.display_dashboard()

    def update_toolbar(self):
        self.toolbar.clear()
        self.toolbar.setStyleSheet("""
            QToolBar { background-color: #83afa5; border: none; padding: 5px; spacing: 5px; margin: 0; }
            QToolBar::separator { width: 1px; margin: 0; }
            QToolButton { border: none; padding: 8px; border: 1px solid black; margin: 0; border-radius: 5px; background-color: #1e2937; }
            QToolButton:hover { background-color: #e0e0e0; }
            QToolButton:pressed { background-color: #d0d0d0; }
            QToolButton:focus { outline: none; border: 1px solid #0078d7; }
        """)
        self.toolbar.setIconSize(QSize(36, 36))
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
        add_action("Open", "icons/open.png", self.open_project_dialog, "Open an Existing Project")
        add_action("", "icons/save.png", self.save_action, "Save Project")
        add_action("", "icons/refresh.png", self.refresh_action, "Refresh View")
        add_action("", "icons/edit.png", self.edit_project_dialog, "Edit Project Name")

        # Play and Pause buttons
        self.play_action = QAction(QIcon("icons/record.png"), "", self)
        self.play_action.triggered.connect(self.start_saving)
        self.play_action.setToolTip("Start Saving Data (Time View)")
        self.toolbar.addAction(self.play_action)

        self.pause_action = QAction(QIcon("icons/pause.png"), "", self)
        self.pause_action.triggered.connect(self.stop_saving)
        self.pause_action.setToolTip("Stop Saving Data (Time View)")
        self.toolbar.addAction(self.pause_action)

        # Enable/disable buttons based on current feature and saving state
        is_time_view = self.current_feature == "Time View"
        self.play_action.setEnabled(is_time_view and not self.is_saving)
        self.pause_action.setEnabled(is_time_view and self.is_saving)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        add_action("Settings", "icons/settings.png", self.settings_action, "Settings")

    def load_projects_async(self):
        def load():
            self.db.load_projects()
            self.tree.clear()
            for project_name in self.db.projects:
                self.add_project_to_tree(project_name)
            QCoreApplication.processEvents()
        QTimer.singleShot(0, load)

    def close_project(self):
        if self.mqtt_handler:
            self.mqtt_handler.stop()
            self.mqtt_handler = None
        self.current_project = None
        self.current_feature = None
        self.is_saving = False
        self.timer.stop()
        self.update_toolbar()
        self.clear_content_layout()
        self.display_dashboard()

    def clear_content_layout(self):
        """Safely clear the content layout and invalidate cached feature instances."""
        logging.debug("Clearing content layout")
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.hide()
                # Remove associated feature instance from cache
                for feature_name, feature_instance in list(self.feature_instances.items()):
                    if feature_instance.get_widget() == widget:
                        logging.debug(f"Removing feature instance: {feature_name}")
                        del self.feature_instances[feature_name]
                widget.deleteLater()
        QCoreApplication.processEvents()

    def open_project_dialog(self):
        projects = self.db.projects
        if not projects:
            QMessageBox.warning(self, "No Projects", "No projects available to open.")
            return
        project_name, ok = QInputDialog.getItem(self, "Open Project", "Select a project:", projects, 0, False)
        if ok and project_name:
            self.current_project = project_name
            self.current_feature = None
            self.is_saving = False
            self.timer.stop()
            self.update_toolbar()
            self.setup_mqtt()
            self.display_feature_content("Create Tags", project_name)

    def display_dashboard(self):
        if self.mqtt_handler:
            self.mqtt_handler.stop()
            self.mqtt_handler = None
        self.current_project = None
        self.current_feature = None
        self.is_saving = False
        self.timer.stop()
        self.update_toolbar()
        self.clear_content_layout()

        header = QLabel("Welcome to Sarayu Application")
        header.setStyleSheet("color: white; font-size: 24px; font-weight: bold; padding: 10px;")
        self.content_layout.addWidget(header, alignment=Qt.AlignCenter)

    def add_project_to_tree(self, project_name):
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
        data = item.data(0, Qt.UserRole)
        if data["type"] == "project":
            self.current_project = data["name"]
            self.current_feature = None
            self.is_saving = False
            self.setup_mqtt()
            self.display_dashboard()
        elif data["type"] == "feature":
            self.current_project = data["project"]
            self.current_feature = data["name"]
            self.is_saving = False
            self.setup_mqtt()
            self.display_feature_content(data["name"], data["project"])

    def create_project(self):
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
            success, message = self.db.create_project(project_name)
            if success:
                self.add_project_to_tree(project_name)
                QMessageBox.information(self, "Success", message)
                self.current_project = project_name
                self.current_feature = None
                self.is_saving = False
                self.update_toolbar()
                self.setup_mqtt()
                self.display_feature_content("Create Tags", project_name)
            else:
                QMessageBox.warning(self, "Error", message)

    def edit_project_dialog(self):
        if not self.current_project:
            QMessageBox.warning(self, "Error", "No project selected to edit!")
            return

        old_project_name = self.current_project
        new_project_name, ok = QInputDialog.getText(self, "Edit Project", "Enter new project name:", text=old_project_name)
        if not ok or not new_project_name or new_project_name == old_project_name:
            return

        success, message = self.db.edit_project(old_project_name, new_project_name)
        if success:
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                if item.text(0) == old_project_name:
                    item.setText(0, new_project_name)
                    item.setData(0, Qt.UserRole, {"type": "project", "name": new_project_name})
                    for j in range(item.childCount()):
                        child = item.child(j)
                        child_data = child.data(0, Qt.UserRole)
                        child_data["project"] = new_project_name
                        child.setData(0, Qt.UserRole, child_data)
                    break
            
            self.current_project = new_project_name
            self.is_saving = False
            self.setup_mqtt()
            self.update_toolbar()
            if self.current_feature:
                self.display_feature_content(self.current_feature, self.current_project)
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Error", message)

    def delete_project(self, project_name):
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {project_name}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            success, message = self.db.delete_project(project_name)
            if success:
                for i in range(self.tree.topLevelItemCount()):
                    if self.tree.topLevelItem(i).text(0) == project_name:
                        self.tree.takeTopLevelItem(i)
                        break
                if self.current_project == project_name:
                    self.close_project()
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.warning(self, "Error", message)

    def start_saving(self):
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
            QMessageBox.warning(self, "Error", f"Failed to start saving: {str(e)}")
            logging.error(f"Failed to start saving: {str(e)}")

    def stop_saving(self):
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
            QMessageBox.warning(self, "Error", f"Failed to stop saving: {str(e)}")
            logging.error(f"Failed to stop saving: {str(e)}")

    def display_feature_content(self, feature_name, project_name):
        """Display the content for a selected feature."""
        logging.debug(f"Displaying feature: {feature_name} for project: {project_name}")
        self.current_project = project_name
        self.current_feature = feature_name
        self.is_saving = False  # Reset saving state when switching features
        self.update_toolbar()

        # Clear existing content
        self.clear_content_layout()

        # Check if feature instance exists and is valid
        feature_instance = self.feature_instances.get(feature_name)
        if feature_instance and feature_instance.project_name == project_name:
            try:
                feature_instance.get_widget().isVisible()  # Check if widget is valid
                logging.debug(f"Reusing cached feature instance: {feature_name}")
                self.content_layout.addWidget(feature_instance.get_widget())
                # Update button states for Time View
                if feature_name == "Time View":
                    self.play_action.setEnabled(not self.is_saving)
                    self.pause_action.setEnabled(self.is_saving)
                return
            except RuntimeError:
                logging.debug(f"Invalid widget for {feature_name}, creating new instance")
                del self.feature_instances[feature_name]
                feature_instance = None

        # Create new feature instance
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
                feature_instance = feature_classes[feature_name](self, self.db, project_name)
                self.feature_instances[feature_name] = feature_instance
                self.content_layout.addWidget(feature_instance.get_widget())
                logging.debug(f"Created new feature instance: {feature_name}")
                # Update button states for Time View
                if feature_name == "Time View":
                    self.play_action.setEnabled(not self.is_saving)
                    self.pause_action.setEnabled(self.is_saving)
            except Exception as e:
                logging.error(f"Failed to load feature {feature_name}: {str(e)}")
                QMessageBox.warning(self, "Error", f"Failed to load {feature_name}: {str(e)}")
        else:
            logging.warning(f"Unknown feature: {feature_name}")

    def save_action(self):
        if self.current_project and self.db.get_project_data(self.current_project):
            QMessageBox.information(self, "Save", f"Data for project '{self.current_project}' saved successfully!")
        else:
            QMessageBox.warning(self, "Save Error", "No project selected to save!")

    def refresh_action(self):
        if self.current_project and self.current_feature:
            self.display_feature_content(self.current_feature, self.current_project)
            QMessageBox.information(self, "Refresh", f"Refreshed view for '{self.current_feature}'!")
        else:
            self.display_dashboard()
            QMessageBox.information(self, "Refresh", "Refreshed dashboard view!")

    def settings_action(self):
        QMessageBox.information(self, "Settings", "Settings functionality not implemented yet.")

    def closeEvent(self, event):
        self.timer.stop()
        if self.mqtt_handler:
            self.mqtt_handler.stop()
        # Clear feature instances
        for feature_name, feature in list(self.feature_instances.items()):
            widget = feature.get_widget()
            widget.hide()
            widget.deleteLater()
            del self.feature_instances[feature_name]
        self.db.close_connection()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    from database import Database
    db = Database(email="user@example.com")
    window = DashboardWindow(db=db, email="user@example.com")
    window.show()
    sys.exit(app.exec_())