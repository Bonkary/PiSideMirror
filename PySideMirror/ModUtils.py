from PySideMirror._constants import *
import config as cfg

class ScreenUtils:
    @staticmethod
    def getScreenResolution():
        return tuple(cfg.Settings.Resolution.split('x'))

class LoggingUtils:
    @staticmethod
    def write(log_message: str) -> None:
        pass

