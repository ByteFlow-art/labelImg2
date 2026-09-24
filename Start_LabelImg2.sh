#!/usr/bin/env bash
# ==============================================================================
#   LabelImg2 - One-Click Launcher for Linux
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_FILE="labelImg.py"

if [ ! -f "$SCRIPT_DIR/$APP_FILE" ]; then
    echo -e "\033[1;31m[ERROR] Cannot find main application file: $APP_FILE\033[0m"
    echo "Directory: $SCRIPT_DIR"
    exit 1
fi

# Detect Wayland / X11 and set Qt platform plugin
if [ -z "$QT_QPA_PLATFORM" ]; then
    if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
        # Default to xcb on Wayland for PyQt5 compatibility if wayland plugin is absent
        export QT_QPA_PLATFORM="xcb;wayland"
    else
        export QT_QPA_PLATFORM="xcb"
    fi
fi

# Prevent Qt MITSHM errors across different X11 displays
export QT_X11_NO_MITSHM=1

PYTHON_CMD=""

# 1. Check local virtual environment (.venv)
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    if "$SCRIPT_DIR/.venv/bin/python" -c "import PyQt5" >/dev/null 2>&1; then
        PYTHON_CMD="$SCRIPT_DIR/.venv/bin/python"
    fi
fi

# 2. Check active Conda environment (labelimg2)
if [ -z "$PYTHON_CMD" ] && [ -n "$CONDA_PREFIX" ]; then
    if [ "$(basename "$CONDA_PREFIX")" = "labelimg2" ]; then
        if python -c "import PyQt5" >/dev/null 2>&1; then
            PYTHON_CMD="python"
        fi
    fi
fi

# 3. Check Conda installation paths for labelimg2
if [ -z "$PYTHON_CMD" ]; then
    for c_path in "$HOME/miniconda3/envs/labelimg2/bin/python" \
                  "$HOME/anaconda3/envs/labelimg2/bin/python" \
                  "/opt/conda/envs/labelimg2/bin/python" \
                  "/opt/miniconda3/envs/labelimg2/bin/python"; do
        if [ -f "$c_path" ]; then
            if "$c_path" -c "import PyQt5" >/dev/null 2>&1; then
                PYTHON_CMD="$c_path"
                break
            fi
        fi
    done
fi

# 4. Check system Python with PyQt5
if [ -z "$PYTHON_CMD" ]; then
    if command -v python3 >/dev/null 2>&1; then
        if python3 -c "import PyQt5" >/dev/null 2>&1; then
            PYTHON_CMD="python3"
        fi
    fi
fi

# If no working Python environment was found, prompt user to run setup_linux.sh
if [ -z "$PYTHON_CMD" ]; then
    echo -e "\033[1;33m[!] No fully configured Python environment found.\033[0m"
    echo -e "\033[1;32m[*] Running automated environment setup (setup_linux.sh)...\033[0m"
    if [ -f "$SCRIPT_DIR/setup_linux.sh" ]; then
        chmod +x "$SCRIPT_DIR/setup_linux.sh"
        bash "$SCRIPT_DIR/setup_linux.sh"
        exec "$SCRIPT_DIR/Start_LabelImg2.sh" "$@"
    else
        echo -e "\033[1;31m[ERROR] Please install dependencies: pip install -r requirements.txt\033[0m"
        exit 1
    fi
fi

# Launch LabelImg2
exec "$PYTHON_CMD" "$SCRIPT_DIR/$APP_FILE" "$@"
