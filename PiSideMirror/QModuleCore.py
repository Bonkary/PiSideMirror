from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from ModUtils import ScreenUtils
from CoreWidgets import *
from PySide6.QtGui import QFont

class QModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setFont(QFont("Arial", 40))
        
        self.row: int = None
        self.column: int = None
        self.rowSpan: int = None
        self.columnSpan: int = None
        
    def setBackgroundColor(self, color):
        pallete = self.palette()
        pallete.setColor(self.backgroundRole(), color)
        self.setPalette(pallete)