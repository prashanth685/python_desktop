from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QSize, QPoint
import logging

class DraggableWidget(QWidget):
    """A widget that supports dragging within its parent."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.drag_start_pos = QPoint(0, 0)
        self.is_maximized = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Only start dragging if not clicking on child widgets (e.g., buttons)
            if not self.childAt(event.pos()):
                self.dragging = True
                self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and not self.is_maximized:
            # Calculate new position
            new_pos = self.mapToParent(event.pos() - self.drag_start_pos)
            parent_widget = self.parentWidget()
            if parent_widget:
                # Constrain within parent boundaries
                parent_rect = parent_widget.rect()
                new_x = max(0, min(new_pos.x(), parent_rect.width() - self.width()))
                new_y = max(0, min(new_pos.y(), parent_rect.height() - self.height()))
                self.move(new_x, new_y)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
        super().mouseReleaseEvent(event)

class FFTViewFeature:
    def __init__(self, parent, db, project_name):
        self.parent = parent  # Reference to DashboardWindow
        self.db = db
        self.project_name = project_name
        self.widget = None
        self.init_widget()

    def init_widget(self):
        """Initialize the FFT feature widget with integrated control bar."""
        self.widget = DraggableWidget()
        self.widget.setStyleSheet("background-color: #34495e; border: 1px solid #2c3e50;")
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        self.widget.setLayout(layout)

        # Control bar
        control_bar = self.create_control_bar()
        layout.addWidget(control_bar)

        # Placeholder for FFT content (e.g., plot)
        fft_content = QLabel("FFT View Placeholder")
        fft_content.setStyleSheet("background-color: #455a64; color: white; padding: 10px;")
        fft_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(fft_content)

    def create_control_bar(self):
        """Create a control bar with Maximize, Minimize, and Cancel buttons."""
        control_bar = QWidget()
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(5)
        control_bar.setLayout(control_layout)

        # Button stylesheet
        button_style = """
            QPushButton {
                color: white;
                font-size: 14px;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
                background-color: #34495e;
                transition: background-color 0.2s ease;
            }
            QPushButton:hover {
                background-color: #4a90e2;
            }
            QPushButton:pressed {
                background-color: #357abd;
            }
        """

        # Maximize button
        maximize_button = QPushButton("⏶")
        maximize_button.setToolTip("Maximize Widget")
        maximize_button.setStyleSheet(button_style)
        maximize_button.clicked.connect(self.maximize_widget)
        control_layout.addWidget(maximize_button)

        # Minimize button
        minimize_button = QPushButton("⏷")
        minimize_button.setToolTip("Minimize Widget")
        minimize_button.setStyleSheet(button_style)
        minimize_button.clicked.connect(self.minimize_widget)
        control_layout.addWidget(minimize_button)

        # Cancel button
        cancel_button = QPushButton("✖")
        cancel_button.setToolTip("Close Widget")
        cancel_button.setStyleSheet(button_style)
        cancel_button.clicked.connect(self.cancel_widget)
        control_layout.addWidget(cancel_button)

        # Spacer to push buttons to the left
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        control_layout.addWidget(spacer)

        return control_bar

    def maximize_widget(self):
        """Maximize the widget to fill the content area."""
        try:
            parent_widget = self.widget.parentWidget()
            if parent_widget:
                self.widget.is_maximized = True
                self.widget.setFixedSize(parent_widget.size())
                self.widget.move(0, 0)
                self.widget.updateGeometry()
                logging.info("FFT widget maximized to fill content area")
        except Exception as e:
            logging.error(f"Error maximizing FFT widget: {str(e)}")

    def minimize_widget(self):
        """Minimize the widget to 200x200 pixels."""
        try:
            self.widget.is_maximized = False
            self.widget.setFixedSize(200, 200)
            self.widget.updateGeometry()
            logging.info("FFT widget minimized to 200x200")
        except Exception as e:
            logging.error(f"Error minimizing FFT widget: {str(e)}")

    def cancel_widget(self):
        """Close the widget and return to the default view."""
        try:
            self.parent.clear_content_layout()
            self.parent.current_feature = None
            self.parent.is_saving = False
            self.parent.display_feature_content("Create Tags", self.project_name)
            logging.info("FFT widget closed, returned to default view")
        except Exception as e:
            logging.error(f"Error canceling FFT widget: {str(e)}")

    def get_widget(self):
        """Return the feature widget."""
        return self.widget

    def on_data_received(self, tag_name, values):
        """Handle incoming MQTT data (placeholder)."""
        pass

    def cleanup(self):
        """Clean up resources."""
        if self.widget:
            self.widget.hide()
            self.widget.deleteLater()
            self.widget = None