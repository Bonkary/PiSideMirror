import signal
import sys
import subprocess
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication
from PiSideMirrorApp import PiSideMirror

def main():
    app = QApplication([])
    app.setApplicationName("PySideMirror")
    app.setApplicationVersion("1.0.0")
    
    window = PiSideMirror()

    def handleSigint(*_):
        window.close()
        app.quit()
        # subprocess.run(['clear'])

    quitShortcut = QShortcut(QKeySequence("Ctrl+Q"), window)
    quitShortcut.setContext(Qt.ApplicationShortcut)
    quitShortcut.activated.connect(handleSigint)

    # Qt's event loop blocks Python's signal handling, so install a handler
    # and wake the interpreter periodically so Ctrl+C is actually processed.
    signal.signal(signal.SIGINT, handleSigint)
    wakeup = QTimer()
    wakeup.start(200)
    wakeup.timeout.connect(lambda: None)

    window.showFullScreen()
    
    print(app.primaryScreen().size())
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
