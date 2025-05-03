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
        self.setStyleSheet("background-color: #e9ecef;")  # Light gray background

        # Main layout for the window
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)

        # Card widget to hold the content
        card_widget = QWidget()
        card_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 15px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                padding: 20px;
                max-height: 600px;
            }
        """)
        card_layout = QVBoxLayout()
        card_widget.setLayout(card_layout)

        # Logo
        logo_label = QLabel(self)
        logo_path = "logo.png" if os.path.exists("logo.png") else "icons/placeholder.png"
        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            logging.warning(f"Could not load logo at {logo_path}")
            pixmap = QPixmap("icons/placeholder.png")
        logo_label.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio))
        logo_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(logo_label)

        # Title
        title_label = QLabel('Select a Project')
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #343a40;
            margin: 15px 0;
        """)
        card_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        # Project combo box
        self.project_combo = QComboBox()
        self.project_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                background-color: #f8f9fa;
                min-width: 300px;
            }
            QComboBox:hover {
                border: 1px solid #007bff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(icons/down_arrow.png);  /* Add a custom arrow icon if available */
                width: 12px;
                height: 12px;
            }
        """)
        self.project_combo.addItem("Select a project...")
        card_layout.addWidget(self.project_combo, alignment=Qt.AlignCenter)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        # Create Project button
        create_button = QPushButton('Create Project')
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #218838;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
        """)
        create_button.clicked.connect(self.create_project)
        button_layout.addWidget(create_button)

        # Open Project button
        open_button = QPushButton('Open Project')
        open_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
        """)
        open_button.clicked.connect(self.open_project)
        button_layout.addWidget(open_button)

        # Back to Login button
        back_button = QPushButton('Back to Login')
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #5a6268;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
        """)
        back_button.clicked.connect(self.back_to_login)
        button_layout.addWidget(back_button)

        card_layout.addLayout(button_layout)
        main_layout.addWidget(card_widget)

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
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("No Projects")
                msg_box.setText("No projects found. Please create a new project.")
                msg_box.setStyleSheet("""
                    background-color: #ffffff;
                    font: 12pt 'Arial';
                    QLabel {
                        color: #343a40;
                    }
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border-radius: 5px;
                        padding: 8px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                """)
                msg_box.exec_()
        except Exception as e:
            logging.error(f"Error loading projects: {str(e)}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to load projects: {str(e)}")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()

    def create_project(self):
        """Create a new project."""
        try:
            project_name, ok = QInputDialog.getText(self, "Create Project", "Enter project name:")
            if ok and project_name:
                success, message = self.db.create_project(project_name)
                if success:
                    self.load_projects()
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("Success")
                    msg_box.setText(message)
                    msg_box.setStyleSheet("""
                        background-color: #ffffff;
                        font: 12pt 'Arial';
                        QLabel {
                            color: #343a40;
                        }
                        QPushButton {
                            background-color: #007bff;
                            color: white;
                            border-radius: 5px;
                            padding: 8px;
                            min-width: 80px;
                        }
                        QPushButton:hover {
                            background-color: #0056b3;
                        }
                    """)
                    msg_box.exec_()
                    logging.info(f"Created new project: {project_name}")
                    self.project_combo.setCurrentText(project_name)
                else:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("Error")
                    msg_box.setText(message)
                    msg_box.setStyleSheet("""
                        background-color: #ffffff;
                        font: 12pt 'Arial';
                        QLabel {
                            color: #343a40;
                        }
                        QPushButton {
                            background-color: #dc3545;
                            color: white;
                            border-radius: 5px;
                            padding: 8px;
                            min-width: 80px;
                        }
                        QPushButton:hover {
                            background-color: #c82333;
                        }
                    """)
                    msg_box.exec_()
        except Exception as e:
            logging.error(f"Error creating project: {str(e)}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to create project: {str(e)}")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()

    def open_project(self):
        """Open the selected project in a new DashboardWindow."""
        project_name = self.project_combo.currentText()
        if project_name == "Select a project..." or not project_name:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Please select a project to open!")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()
            return
        if project_name not in self.db.projects:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Project '{project_name}' not found!")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()
            self.load_projects()
            return
        try:
            if project_name in self.open_dashboards and self.open_dashboards[project_name].isVisible():
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Info")
                msg_box.setText(f"Project '{project_name}' is already open!")
                msg_box.setStyleSheet("""
                    background-color: #ffffff;
                    font: 12pt 'Arial';
                    QLabel {
                        color: #343a40;
                    }
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border-radius: 5px;
                        padding: 8px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                """)
                msg_box.exec_()
                self.open_dashboards[project_name].raise_()
                self.open_dashboards[project_name].activateWindow()
                return

            logging.info(f"Opening project: {project_name}")
            dashboard = DashboardWindow(self.db, self.email, project_name, self)
            dashboard.show()
            self.open_dashboards[project_name] = dashboard
        except Exception as e:
            logging.error(f"Error opening Dashboard for project {project_name}: {str(e)}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to open dashboard: {str(e)}")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()

    def back_to_login(self):
        """Return to the login window."""
        try:
            self.auth_window.show()
            self.auth_window.showMaximized()
            self.close()
        except Exception as e:
            logging.error(f"Error returning to login: {str(e)}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to return to login: {str(e)}")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()

    def closeEvent(self, event):
        """Handle window close event."""
        try:
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