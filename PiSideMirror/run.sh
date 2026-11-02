#!/bin/bash
# Launches PySideMirror inside labwc (a minimal Wayland compositor) so the
# display can be rotated. Run from the Pi's console (not over SSH), as a user
# in the video, input and render groups. Needs: labwc, wlr-randr.
#
# MIRROR_TRANSFORM: wlr-randr transform used when "portrait" is true
# (default 90; use 270 if the picture comes out upside down).

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

if [ -f "$SCRIPT_DIR/main.py" ]; then
    MAIN="$SCRIPT_DIR/main.py"
else
    MAIN="$SCRIPT_DIR/PiSideMirror/main.py"
fi

PYTHON="python3"
for candidate in "$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/../venv/bin/python"; do
    [ -x "$candidate" ] && PYTHON="$candidate" && break
done

# Runs inside the labwc session (labwc starts this script with --inner)
if [ "$1" = "--inner" ]; then
    CONFIG="$(dirname "$MAIN")/config.json"
    if "$PYTHON" -c "import json,sys; sys.exit(0 if json.load(open('$CONFIG'))['settings']['portrait'] else 1)" 2>/dev/null; then
        # The output may not be ready the instant the session starts
        for _ in 1 2 3 4 5 6 7 8 9 10; do
            OUTPUT="$(wlr-randr 2>/dev/null | awk 'NR==1 {print $1}')"
            [ -n "$OUTPUT" ] && break
            sleep 0.5
        done
        [ -n "$OUTPUT" ] && wlr-randr --output "$OUTPUT" --transform "${MIRROR_TRANSFORM:-90}"
    fi

    QT_QPA_PLATFORM=wayland "$PYTHON" "$MAIN"

    # labwc keeps running after its startup command ends, so shut it down
    labwc --exit
    exit
fi

# labwc needs a runtime dir; a console login without logind may not set one
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR="/run/user/$(id -u)"
    mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"
fi

exec labwc -s "$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}") --inner"
