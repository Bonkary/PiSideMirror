from _constants import *
import config as cfg
import inspect

type _ModuleName = str

class ScreenUtils:
    @staticmethod
    def getScreenResolution():
        res = tuple(cfg.Settings.Resolution.split('x'))
        width = int(res[0]) if not cfg.Settings.Portrait else int(res[1])
        height = int(res[1]) if not cfg.Settings.Portrait else int(res[0])
        return (width, height)

    @staticmethod
    def getTotalGridSize():
        screenRes = cfg.Settings.Resolution

        width = int(cfg.Settings.Resolution.split('x')[0]) if cfg.Settings.Portrait else int(cfg.Settings.Resolution.split('x')[1])
        width = width // 2

        height = int(cfg.Settings.Resolution.split('x')[1]) if cfg.Settings.Portrait else int(cfg.Settings.Resolution.split('x')[0])
        height = height // 4

        return width, height

class LoggingUtils:
    @staticmethod
    def addToLog(log_message: str, module: _ModuleName | None = None) -> None:
        if not module:
            caller = inspect.currentframe().f_back
            callerObject = caller.f_locals.get("self")
            module = callerObject.__class__.__name__ if callerObject else "Unknown"
            print(module)

