import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QComboBox, QMessageBox, QApplication, QInputDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import os
from dashboard import DashboardWindow
from database import Database
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ProjectSelectionWindow(QWidget):
    def __init__(self, db, email, auth_window):
        super().__init__()
        self.db = db
        self.email = email
        self.auth_window = auth_window
        self.open_dashboards = {}  # Track open dashboard windows by project name
        self.initUI()
        self.load_projects()

    def initUI(self):
        self.setWindowTitle('Project Selection - Sarayu Infotech Solutions')
        self.showMaximized()
        self.setStyleSheet("background-color: #f0f0f0;")

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)

        logo_label = QLabel(self)
        logo_path = "logo.png" if os.path.exists("logo.png") else "icons/placeholder.png"
        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            logging.warning(f"Could not load logo at {logo_path}")
            pixmap = QPixmap("icons/placeholder.png")
        logo_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio))
        logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(logo_label)

        title_label = QLabel('Select a Project')
        title_label.setStyleSheet("font-size: 30px; font-weight: bold; color: #007bff; margin: 20px;")
        main_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        self.project_combo = QComboBox()
        self.project_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 5px;
                padding: 10px;
                font-size: 25px;
                min-width: 400px;
            }
            QComboBox:hover {
                border: 2px solid #007bff;
            }
        """)
        self.project_combo.addItem("Select a project...")
        main_layout.addWidget(self.project_combo, alignment=Qt.AlignCenter)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        create_button = QPushButton('Create Project')
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 25px;
                min-width: 150px;
                border-radius:50%;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        create_button.clicked.connect(self.create_project)
        button_layout.addWidget(create_button)

        open_button = QPushButton('Open Project')
        open_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 25px;
                min-width: 150px;
                border-radius:50px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        open_button.clicked.connect(self.open_project)
        button_layout.addWidget(open_button)
        

        back_button = QPushButton('Back to Login')
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 25px;
                min-width: 150px;
                border-radius:50px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        back_button.clicked.connect(self.back_to_login)
        button_layout.addWidget(back_button)

        main_layout.addLayout(button_layout)

    def load_projects(self):
        """Load projects from the database into the combo box."""
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            self.project_combo.clear()
            self.project_combo.addItem("Select a project...")
            self.db.load_projects()
            for project_name in self.db.projects:
                self.project_combo.addItem(project_name)
            logging.info(f"Loaded projects into combo box: {self.db.projects}")
            if not self.db.projects:
                QMessageBox.information(self, "No Projects", "No projects found. Please create a new project.")
        except Exception as e:
            logging.error(f"Error loading projects: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load projects: {str(e)}")
            QMessageBox.setStyleSheet("""
                QMessageBox {
                    background-color: #ffdddd;
                    font: bold 12pt 'Arial';
                }
                QLabel {
                    color: #aa0000;
                }
                QPushButton {
                    background-color: #aa0000;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #cc0000;
                }
            """)

    def create_project(self):
        """Create a new project."""
        try:
            project_name, ok = QInputDialog.getText(self, "Create Project", "Enter project name:")
            if ok and project_name:
                # Call the Database class's create_project method
                success, message = self.db.create_project(project_name)
                if success:
                    self.load_projects()  # Refresh project list
                    QMessageBox.information(self, "Success", message)
                    logging.info(f"Created new project: {project_name}")
                    # Automatically select the new project
                    self.project_combo.setCurrentText(project_name)
                else:
                    QMessageBox.warning(self, "Error", message)
        except Exception as e:
            logging.error(f"Error creating project: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")

    def open_project(self):
        """Open the selected project in a new DashboardWindow."""
        project_name = self.project_combo.currentText()
        if project_name == "Select a project..." or not project_name:
            QMessageBox.warning(self, "Error", "Please select a project to open!")
            return
        if project_name not in self.db.projects:
            QMessageBox.warning(self, "Error", f"Project '{project_name}' not found!")
            self.load_projects()  # Refresh project list
            return
        try:
            # Check if a dashboard for this project is already open
            if project_name in self.open_dashboards and self.open_dashboards[project_name].isVisible():
                QMessageBox.information(self, "Info", f"Project '{project_name}' is already open!")
                self.open_dashboards[project_name].raise_()  # Bring the window to the front
                self.open_dashboards[project_name].activateWindow()
                return

            logging.info(f"Opening project: {project_name}")
            dashboard = DashboardWindow(self.db, self.email, project_name, self)
            dashboard.show()
            self.open_dashboards[project_name] = dashboard
        except Exception as e:
            logging.error(f"Error opening Dashboard for project {project_name}: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open dashboard: {str(e)}")

    def back_to_login(self):
        """Return to the login window."""
        try:
            self.auth_window.show()
            self.auth_window.showMaximized()
            self.close()
        except Exception as e:
            logging.error(f"Error returning to login: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to return to login: {str(e)}")

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Close all open dashboard windows
            for dashboard in self.open_dashboards.values():
                if dashboard.isVisible():
                    dashboard.close()
            if self.db.is_connected():
                self.db.close_connection()
        except Exception as e:
            logging.error(f"Error closing database connection: {str(e)}")
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    db = Database(email="user@example.com")
    window = ProjectSelectionWindow(db, "user@example.com", None)
    window.show()
    sys.exit(app.exec_())