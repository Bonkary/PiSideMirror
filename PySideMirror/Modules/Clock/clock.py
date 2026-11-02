from CoreWidgets import *
from PySideMirror.QModuleCore import QModule

class Clock(QModule):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.gridSize = (1, 1)
        
        self.label = QLabel("Clock", self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.setBackgroundColor('blue')