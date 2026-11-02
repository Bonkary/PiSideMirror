from dataclasses import dataclass
from typing import ClassVar
from pathlib import Path

@dataclass
class SettingNames:
    Resolution: str = "screenResolution"
    Rotate: str = "rotate"

@dataclass
class ConfigOptions:
    Modules: str = "modules"
    Settings: str = "settings"
    Defaults: ClassVar[dict] = {
        SettingNames.Resolution: "1080x1920",
        SettingNames.Rotate: False
    }

@dataclass
class Dirs:
    Base = Path(__file__).parent
    UserHome = Path.home()
    Modules = Base / "Modules"
    Temp = Path("/tmp")
    UserConfig = UserHome / "config"
    Logs = UserHome / ".MirrorLogs"

@dataclass
class Files:
    Config = Dirs.UserConfig / "mirror.json"
    AppLog = Dirs.Logs / ".mirror.log"