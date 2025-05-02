import sys
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QFormLayout, QApplication,
                             QGraphicsDropShadowEffect, QHBoxLayout)
from PyQt5.QtCore import Qt
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import bcrypt
import os
# Assuming Database and ProjectSelectionWindow are defined elsewhere
from database import Database
from project_selection import ProjectSelectionWindow

class AuthWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.client = None
        self.db = None
        self.users_collection = None
        self.initDB()
        self.initUI()
        self.setWindowState(Qt.WindowMaximized)
        
    def initDB(self):
        try:
            self.client = MongoClient("mongodb://localhost:27017/")
            self.db = self.client["sarayu_db"]
            self.users_collection = self.db["users"]
            print("Connected to MongoDB successfully!")
        except ConnectionFailure as e:
            print(f"Could not connect to MongoDB: {e}")
            QMessageBox.critical(self, "Database Error", "Failed to connect to the database.")
            sys.exit(1)

    def initUI(self):
        self.setWindowTitle('Sarayu Infotech Solutions Pvt. Ltd.')
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        # Logo
        logo_label = QLabel(self)
        logo_path = "logo.png" if os.path.exists("logo.png") else "icons/placeholder.png"
        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            print(f"Warning: Could not load logo at {logo_path}")
            pixmap = QPixmap("icons/placeholder.png")
        logo_label.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio))
        logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(logo_label)

        # Company name
        company_label = QLabel('Sarayu Infotech Solutions Pvt. Ltd.')
        company_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #007bff;")
        main_layout.addWidget(company_label, alignment=Qt.AlignCenter)

        # Welcome text
        welcome_label = QLabel('Welcome')
        welcome_label.setStyleSheet("font-size: 20px; color: #007bff;")
        main_layout.addWidget(welcome_label, alignment=Qt.AlignCenter)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_login_tab(), "Login")
        self.tabs.addTab(self.create_signup_tab(), "Signup")
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 10px 20px;
                border-radius: 5px;
                margin: 5px;
                font-weight: bold;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #d3d3d3;
            }
        """)
        self.tabs.setFixedWidth(400)
        # self.tabs.tabBar().setAlignment(Qt.AlignCenter)  # Center align tabs
        
        main_layout.addWidget(self.tabs, alignment=Qt.AlignCenter)
        self.setStyleSheet("background-color: white;")

    def create_input_field(self, placeholder):
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        input_field.setStyleSheet("""
            QLineEdit {
                background: white;
                border: none;
                padding: 12px 20px;
                border-radius: 20px;
                border: 2px solid transparent;
                color: rgb(170, 170, 170);
                font-size: 14px;
                width: 290px;
            }
            QLineEdit:focus {
                border: 2px solid #12B1D1;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setOffset(0, 10)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor("#cff0ff"))
        input_field.setGraphicsEffect(shadow)
        return input_field

    def create_shadow_effect(self):
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setOffset(0, 30)
        shadow_effect.setBlurRadius(30)
        shadow_effect.setColor(QColor(133, 189, 215, 223))
        return shadow_effect

    def create_container(self, layout):
        container = QWidget()
        container.setLayout(layout)
        container.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #FFFFFF, stop:1 #F4F7FB);
            border-radius: 40px;
            border: 5px solid white;
            padding: 25px 35px;
        """)
        shadow = self.create_shadow_effect()
        container.setGraphicsEffect(shadow)
        return container

    def create_login_tab(self):
        login_tab = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        # Heading
        heading = QLabel("Sign In")
        heading.setStyleSheet("font-size: 30px; font-weight: bold; color: rgb(16, 137, 211);text-align:center")
        heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(heading)

        # Form
        form_layout = QFormLayout()
        form_layout.setAlignment(Qt.AlignCenter)
        form_layout.setSpacing(10)

        # Email input
        email_label = QLabel('Email')
        email_label.setStyleSheet("font-size: 18px; color: #333; font-weight: bold;")
        self.login_email_input = self.create_input_field('Enter your email')
        self.login_email_input.setText('sarayu@gmail.com')
        form_layout.addRow(email_label, self.login_email_input)

        # Password input
        password_label = QLabel('Password')
        password_label.setStyleSheet("font-size: 18px; color: #333; font-weight: bold;")
        self.login_password_input = self.create_input_field('Enter your password')
        self.login_password_input.setText('12345678')
        self.login_password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow(password_label, self.login_password_input)

        # Forgot password link
        forgot_link = QLabel('<a href="#" style="color: #0099ff; text-decoration: none; font-size: 11px;">Forgot Password?</a>')
        forgot_link.setOpenExternalLinks(True)
        form_layout.addRow("", forgot_link)

        layout.addLayout(form_layout)

        # Sign in button
        signin_button = QPushButton('Sign In')
        signin_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgb(16, 137, 211), stop:1 rgb(18, 177, 209));
                color: white;
                border-radius: 20px;
                padding: 15px;
                font-weight: bold;
                border: none;
                width: 290px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgb(14, 123, 190), stop:1 rgb(16, 159, 188));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgb(12, 110, 170), stop:1 rgb(14, 141, 168));
            }
        """)
        shadow_button = QGraphicsDropShadowEffect()
        shadow_button.setOffset(0, 20)
        shadow_button.setBlurRadius(10)
        shadow_button.setColor(QColor(133, 189, 215, 223))
        signin_button.setGraphicsEffect(shadow_button)
        signin_button.clicked.connect(self.login)
        layout.addWidget(signin_button, alignment=Qt.AlignCenter)



        # Agreement link
        agreement_link = QLabel('<a href="#" style="color: #0099ff; text-decoration: none; font-size: 9px;">Learn user licence agreement</a>')
        agreement_link.setOpenExternalLinks(True)
        layout.addWidget(agreement_link, alignment=Qt.AlignCenter)

        return self.create_container(layout)

    def create_signup_tab(self):
        signup_tab = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        # Heading
        heading = QLabel("Sign Up")
        heading.setStyleSheet("font-size: 30px; font-weight: bold; color: rgb(16, 137, 211);")
        heading.setAlignment(Qt.AlignCenter)

        layout.addWidget(heading)

        # Form
        form_layout = QFormLayout()
        form_layout.setAlignment(Qt.AlignCenter)
        form_layout.setSpacing(10)

        # Email input
        email_label = QLabel('Email')
        email_label.setStyleSheet("font-size: 18px; color: #333; font-weight: bold;")
        self.signup_email_input = self.create_input_field('Enter your email')
        form_layout.addRow(email_label, self.signup_email_input)

        # Password input
        password_label = QLabel('Password')
        password_label.setStyleSheet("font-size: 18px; color: #333; font-weight: bold;")
        self.signup_password_input = self.create_input_field('Enter your password')
        self.signup_password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow(password_label, self.signup_password_input)

        # Confirm password input
        confirm_password_label = QLabel('Confirm Password')
        confirm_password_label.setStyleSheet("font-size: 18px; color: #333; font-weight: bold;")
        self.signup_confirm_password_input = self.create_input_field('Confirm your password')
        self.signup_confirm_password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow(confirm_password_label, self.signup_confirm_password_input)

        layout.addLayout(form_layout)

        # Sign up button
        signup_button = QPushButton('Sign Up')
        signup_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #28a745, stop:1 #218838);
                color: white;
                border-radius: 20px;
                padding: 15px;
                font-weight: bold;
                border: none;
                width: 290px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #218838, stop:1 #1e7e34);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e7e34, stop:1 #1a6b2d);
            }
        """)
        shadow_button = QGraphicsDropShadowEffect()
        shadow_button.setOffset(0, 20)
        shadow_button.setBlurRadius(10)
        shadow_button.setColor(QColor(133, 189, 215, 223))
        signup_button.setGraphicsEffect(shadow_button)
        signup_button.clicked.connect(self.signup)
        layout.addWidget(signup_button, alignment=Qt.AlignCenter)

        return self.create_container(layout)

    def login(self):
        email = self.login_email_input.text().strip()
        password = self.login_password_input.text().strip()
        
        if not email or not password:
            QMessageBox.warning(self, "Input Error", "Please enter both email and password.")
            return
        
        user = self.users_collection.find_one({"email": email})
        if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
            try:
                db = Database(connection_string="mongodb://localhost:27017/", email=email)
                self.project_selection = ProjectSelectionWindow(db, email, self)
                self.project_selection.show()
                self.hide()
            except Exception as e:
                print(f"Error opening Project Selection: {e}")
                QMessageBox.critical(self, "Error", f"Failed to open project selection: {e}")
        else:
            QMessageBox.warning(self, "Login Failed", "Incorrect email or password.")

    def signup(self):
        email = self.signup_email_input.text().strip()
        password = self.signup_password_input.text().strip()
        confirm_password = self.signup_confirm_password_input.text().strip()
        
        if not email or not password or not confirm_password:
            QMessageBox.warning(self, "Input Error", "Please fill in all fields.")
            return
            
        if password != confirm_password:
            QMessageBox.warning(self, "Input Error", "Passwords do not match.")
            return
            
        if self.users_collection.find_one({"email": email}):
            QMessageBox.warning(self, "Signup Failed", "User with this email already exists. Please log in.")
            return
            
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = {"email": email, "password": hashed_password}
        try:
            self.users_collection.insert_one(user_data)
            email_safe = email.replace('@', '_').replace('.', '_')
            self.db[f"tagcreated_{email_safe}"].insert_one({"init": True})
            self.db[f"mqttmessage_{email_safe}"].insert_one({"init": True})
            QMessageBox.information(self, "Success", "Signup successful! Please log in.")
            self.tabs.setCurrentIndex(0)
            self.signup_email_input.clear()
            self.signup_password_input.clear()
            self.signup_confirm_password_input.clear()
        except Exception as e:
            print(f"Error inserting user: {e}")
            QMessageBox.critical(self, "Database Error", "Failed to sign up.")

    def closeEvent(self, event):
        if self.client:
            self.client.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AuthWindow()
    window.show()
    sys.exit(app.exec_())