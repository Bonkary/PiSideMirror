# PySideMirror
A GUI based on PySide6 for Smart Mirrors. This is just a personal project and kinda seeing what this becomes lol... I tried to make this AS EASY as I could for other's to use.

#### How it works
It just imports every Class inside the Modules folder, and recursively adds them based on their Module.json file positioning. There can be overlap between the widgets, but thats just based on how you configure it. Maybe you want that. Who knows.

--------------------

### Adding a Module
Make a directory in `modules` with the name of the Module and move the files in there.  

##### Structure
```
PySideMirror
└── Modules
    └── ModuleName
        ├── __init__.py         # This is the most important bit.
        ├── module.py           # You can name this whatever, really.
        └── ModuleName.json     # This is made by PySideMirror after it starts
```
----------------------
### Creating a Module
You can use ModUtils.py for utility functions like `getScreenResolution()` and `write_to_log()` to help
##### module.py
```
from QModuleBase import QModule
from ModUtils import LoggingUtils

class Calendar(QModule):
    def __init__(self, parent=None):
        super().__init__(parent)

        # You must have 'gridSize' attribute!
        # Otherwise, your module will be ignored.
        self.gridSize = (1, 2)  # Uses 1 Row and 2 Columns

        # Other module code below
    
    def addEvent(eventName: str, date: tuple[int,int,int]) -> bool:
        # addEvent Logic Here
        LoggingUtils.write_to_log("Added event {eventName} to Calendar!")


```

##### __init\__.py
```
from module import ModuleName      # Only import your Module!

__all__ = ["ModuleName"]           # Only allow "ModuleName" to be imported by the Mirror.
```


##### Module.json
```
{
    "position": {
        "row": 0,
        "column": 1
    },
    "visible": true
}
```
-----------------------

