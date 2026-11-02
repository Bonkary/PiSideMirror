import json
from dataclasses import dataclass
from _constants import SettingNames, ConfigOptions, Files
import os
from typing import ClassVar

if not os.path.exists(Files.Config):
    Files.Config.touch()

with open(Files.Config, "r+") as f:
    CONFIG = f.read()
    if not CONFIG:
        CONFIG = ConfigOptions.Defaults
        f.write(json.dumps(CONFIG))
        f.seek(0)
    else:
        CONFIG = json.loads(CONFIG)

_SETTINGS = CONFIG[ConfigOptions.Settings]
_MODULES = CONFIG[ConfigOptions.Modules]

@dataclass
class Settings:
    Resolution: str = _SETTINGS[SettingNames.Resolution]
    Portrait: bool = _SETTINGS[SettingNames.Portrait]
    Modules: ClassVar[list] = _MODULES