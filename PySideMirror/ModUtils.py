from PySideMirror._constants import *
import config as cfg
import inspect

type _ModuleName = str

class ScreenUtils:
    @staticmethod
    def getScreenResolution():
        return tuple(cfg.Settings.Resolution.split('x'))

class LoggingUtils:
    @staticmethod
    def write(log_message: str, module: _ModuleName | None = None) -> None:
        if not module:
            caller = inspect.currentframe().f_back
            callerObject = caller.f_locals.get("self")
            module = callerObject.__class__.__name__ if callerObject else "Unknown"
            print(module)

