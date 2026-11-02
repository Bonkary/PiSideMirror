#!/bin/bash

PYSIDE_MIRROR_DIR="/home/$USER/PySideMirror"
VENV_PATH="$PYSIDE_MIRROR_DIR/venv"

create_env() {
    python3.13 -m venv "$VENV_PATH"
    "$VENV_PATH/bin/python" -m pip install -r "$PYSIDE_MIRROR_DIR/requirements.txt"
    printf '\nalias pysidemirror="%s %s/main.py"\n' "$VENV_PATH/bin/python" "$PYSIDE_MIRROR_DIR" | tee -a ~/.bashrc

}




mkdir ~/.MirrorLogs

