from CoreWidgets import *
from QModuleCore import QModule
import _utils as utils
import config as cfg
import Modules
from _constants import *
import os
import json
from exceptions import *
from ModUtils import LoggingUtils

class PySideMirror(CoreWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.moduleWidgets = []
        
        self.setBackgroundColor('black')
        columnWidth, rowHeight = utils.calculate_grid_size()
        
        mainLayout = CoreGridLayout()
        mainLayout.setColumnMinimumWidth(0, columnWidth)
        mainLayout.setColumnMinimumWidth(1, columnWidth)
        
        mainLayout.setRowMinimumHeight(0, rowHeight)
        mainLayout.setRowMinimumHeight(1, rowHeight)
        mainLayout.setRowMinimumHeight(2, rowHeight)
        
        moduleNames = [module for module in dir(Modules) if not "_" in str(module)]
        for moduleName in moduleNames:
            moduleDataPath = Dirs.Modules / moduleName / f"{moduleName}.json"
            moduleDataPath.touch(exist_ok=True)
            
            try:
                module: QModule = getattr(Modules, moduleName)()
            except AttributeError:
                LoggingUtils.write(f"Unable to find Module {moduleName}. Skipping.")
                LoggingUtils.write(f"Failed to find.", module=moduleNames)
                continue

            try:
                moduleSize: tuple[int,int] = getattr(module, "gridSize")
            except AttributeError:
                LoggingUtils.write(f"Can't map {moduleName} since it's missing the 'gridSize' attribute. Skipping.")
                continue
            
            data = moduleDataPath.read_text()
            if data:
                data: dict = json.loads(data)
                mainLayout.addWidget(
                    module, 
                    data["position"]['row'],
                    data["position"]['column'],
                    moduleSize[0],
                    moduleSize[1]
                )
                module.setVisible(data["visible"])
            else:
                data = {
                    "position": [],
                    "visible": False
                }
                Files.Config.write_text(json.dumps(data))
                
            LoggingUtils.write(f"Imported {moduleName} successfully.")
            
        self.setLayout(mainLayout)
        
        
        