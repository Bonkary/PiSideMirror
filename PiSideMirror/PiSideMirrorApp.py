from CoreWidgets import *
from QModuleCore import QModule
import _utils as utils
import config as cfg
import Modules
from _constants import *
import os
import json
from exceptions import *
from ModUtils import LoggingUtils, ScreenUtils

POPULATED_COORDS: list[tuple[int,int]] = []

class PiSideMirror(CoreWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.moduleWidgets = []
    
        # screenWidth, screenHeight = ScreenUtils.getScreenResolution()
        
        self.setFixedSize(*ScreenUtils.getScreenResolution())
        
        self.setBackgroundColor('black')
        columnWidth, rowHeight = ScreenUtils.getTotalGridSize()
        
        mainLayout = CoreGridLayout()
        mainLayout.setSpacing(100)
        mainLayout.setColumnMinimumWidth(0, columnWidth)
        mainLayout.setColumnMinimumWidth(1, columnWidth)
        
        mainLayout.setRowMinimumHeight(0, rowHeight)
        mainLayout.setRowMinimumHeight(1, rowHeight)
        mainLayout.setRowMinimumHeight(2, rowHeight)
        mainLayout.setRowMinimumHeight(3, rowHeight)
        
        moduleNames = [module for module in dir(Modules) if not "_" in str(module)]
        for moduleName in moduleNames:
            moduleDataPath = Dirs.Modules / moduleName / "config.json"
            moduleDataPath.touch(exist_ok=True)
            
            try:
                module: QModule = getattr(Modules, moduleName)()
            except AttributeError:
                Files.AppLog.write_text(f"\nUnable to find Module {moduleName}. Skipping.")
                LoggingUtils.addToLog(f"Unable to find this module. Check __init__.py", module=moduleNames)
                continue
            
            try:
                moduleSize: tuple[int,int] = getattr(module, "gridSize")
            except AttributeError:
                Files.AppLog.write_text(f"\nCan't map {moduleName} since it's missing the 'gridSize' attribute. Skipping.")
                LoggingUtils.addToLog(f"Missing 'gridSize' attribute in this module's __init__", module=moduleNames)
                continue
            
            data = moduleDataPath.read_text()
            if data:
                data: dict = json.loads(data)
                mainLayout.addWidget(
                    module, 
                    data["position"]['row'],
                    data["position"]['column'],
                    moduleSize[0],
                    moduleSize[1],
                )
                module.setVisible(data["visible"])
                
            else:
                data = {
                    "position": [],
                    "visible": False
                }
                Files.Config.write_text(json.dumps(data))
                
            Files.AppLog.write_text(f"\nImported {moduleName} successfully.")
            LoggingUtils.addToLog("Imported successfully", module=moduleName)
            
        self.setLayout(mainLayout)
        
        
        