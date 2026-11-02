from dataclasses import dataclass
from typing import ClassVar
from pathlib import Path

@dataclass
class SettingNames:
    Resolution: str = "screenResolution"
    Portrait: str = "portrait"

@dataclass
class ConfigOptions:
    Modules: str = "modules"
    Settings: str = "settings"
    Defaults: ClassVar[dict] = {
        SettingNames.Resolution: "1080x1920",
        SettingNames.Portrait: False
    }

@dataclass
class Dirs:
    Base = Path(__file__).parent
    Modules = Base / "Modules"
    Temp = Path("/tmp")
    Logs = Base / "Logs"

@dataclass
class Files:
    Config = Dirs.Base / "config.json"
    AppLog = Dirs.Logs / "mirror.log"
    
Files.Config.touch(exist_ok=True)
Files.AppLog.touch(exist_ok=True)
Dirs.Modules.touch(exist_ok=True)