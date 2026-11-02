# PiSideMirror

### Description
A modular GUI display system based on PySide6 for Smart Mirrors. It's built with using a Raspberry Pi in mind. This is just a personal project and kinda seeing what this becomes lol... I tried to make this as easy to use as I could for other's.

This app does kinda assume you're working with a 1080p monitor. 

---------------

### Dependencies
If you are running a headless OS, then you need:
```
sudo apt install cage wlr-randr
```
*Note: or your equivalent if not on a Pi or Debian-based distro* 

----------------

### Installation
```
curl -fsSL https://raw.githubusercontent.com/Bonkary/PySideMirror/install.sh | bash
```

-----------------

### Adding a Module
Make a directory in `Modules` with the name of the Module and move the files in there.  
```
PySideMirror
└── Modules
    └── ModuleName
        ├── __init__.py
        ├── module.py
        └── config.json
```
----------------------

### Basic Troubleshooting
You can look inside the `~/.MirrorLogs` folder for log files. Each of your Modules will have their own seperate log to look into.

#### My Newly Added Module Isn't Showing!
Make sure the name inside `__all__` in `__init__.py` matches the `ModuleName`.
```
# Correct
from module import ModuleName

__all__ = ["ModuleName"]


# Incorrect
import module

__all__ = ["module"]


# Incorrect
from module import ModuleName

__all__ = ["Anything that isnt ModuleName"]
```

