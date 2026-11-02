## Building a Module for PySideMirror
If you know PySide6, then it should be pretty easy. All you need to do is create a QModule (basically just a QWidget with some extra functions).

If you don't know PySide6, get to learnin'.

When developing, you should do it from inside the Modules folder. This way you can take advantage of some of the tools that I have provided. Plus it keeps everything simple for the user if you let me handle certain things lol

--------------------

### How it works
It just imports every Class inside the `Modules` folder, and recursively adds them based on their `ModuleName.json` file positioning. There can be overlap between the widgets, but thats just based on how you configure it. Maybe you want that. Who knows.

You can look further into it inside the `PySideMirror` class.

--------------------

### Adding a Module
Make a directory in `Modules` with the name of your Module and move the files in there.
```
PySideMirror
└── Modules
    └── ModuleName
        ├── __init__.py         # This is the most important bit.
        ├── module.py           # You can name this whatever, really.
        └── ModuleName.json     # This is made by PySideMirror after it starts
```
----------------------
### Log Files
If a Module isn't working correctly, you can look inside the `~/.MirrorLogs` directory to
see what went wrong with them. Each Module will have its own seperate log file.

To use Logging for your module, use the `LoggingUtils` inside the `ModUtils.py` file.  
It will create a seperate log for just your Module without you needing to specify the file yourself. Your log will be in `~/.MirrorLogs/ModuleName/ModuleName.log`

-----------------------

### Creating a Module
##### module.py
```
from QModuleCore import QModule
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
        LoggingUtils.addToLog("Added event {eventName} to Calendar!")
```

##### __init\__.py
```
from module import ModuleName      # Only import your Module!

__all__ = ["ModuleName"]           # Only allow "ModuleName" to be imported by the Mirror.
```

##### config.json
You can add what you need for your module in here. It is also used by PySideMirror's, so you need to keep:
```
{
    "position": {
        "row": 0,
        "column": 0
    },
    visible: true
}
```

Other than that, you can add whatever other configuration options you'd like.

-----------------------