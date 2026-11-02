from CoreWidgets import *
from PySideMirror.QModuleCore import QModule

class Calendar(QModule):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.gridSize = (2, 1)
        
        self.label = QLabel("Calendar", self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.setBackgroundColor('green')