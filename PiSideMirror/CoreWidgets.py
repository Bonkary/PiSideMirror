from PySide6.QtWidgets import (
    QWidget, QMainWindow, QGridLayout,
    QLabel, QVBoxLayout, QStackedLayout,
    QHBoxLayout
)
from PySide6.QtCore import Qt

class CoreStackedLayout(QStackedLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

class CoreGridLayout(QGridLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

class CoreVBoxLayout(QVBoxLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)
        
class CoreHBoxLayout(QHBoxLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

class CoreWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        
    def setBackgroundColor(self, color):
        pallete = self.palette()
        pallete.setColor(self.backgroundRole(), color)
        self.setPalette(pallete)