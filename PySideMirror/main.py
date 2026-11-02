import signal
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySideMirrorApp import PySideMirror

def main():
    app = QApplication([])
    app.setApplicationName("PySideMirror")
    app.setApplicationVersion("1.0.0")
    
    # Qt's event loop blocks Python's signal handling, so install a handler
    # and wake the interpreter periodically so Ctrl+C is actually processed.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    wakeup = QTimer()
    wakeup.start(200)
    wakeup.timeout.connect(lambda: None)

    window = PySideMirror()
    window.showFullScreen()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
