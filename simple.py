import sys
import os
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow
from PyQt5.QtGui import QPixmap, QIcon

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Icon Loader")
        self.setGeometry(100, 100, 400, 300)

        # Load window icon
        self.setWindowIcon(QIcon(resource_path("icons/logo.png")))

        # Show image
        label = QLabel(self)
        pixmap = QPixmap(resource_path("icons/logo.png"))
        label.setPixmap(pixmap)
        label.resize(pixmap.width(), pixmap.height())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
