import subprocess
import config as cfg
import json
from _constants import SettingNames, ConfigOptions

def calculate_grid_size():
    screenRes = cfg.Settings.Resolution
    
    width = int(cfg.Settings.Resolution.split('x')[0]) if cfg.Settings.Rotate else int(cfg.Settings.Resolution.split('x')[1])
    width = width // 2
    
    height = int(cfg.Settings.Resolution.split('x')[1]) if cfg.Settings.Rotate else int(cfg.Settings.Resolution.split('x')[0])
    height = height // 4
    
    return width, height

def write_config():
    config = {
        ConfigOptions.Settings: {
            SettingNames.Resolution: cfg.Settings.Resolution,
            SettingNames.Rotate: cfg.Settings.Rotate
        },
        ConfigOptions.Modules: cfg._MODULES
    }
    
    with open("config.json", "w") as f:
        f.write(json.dumps(config, indent=4))