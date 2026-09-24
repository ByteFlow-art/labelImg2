#!/usr/bin/env bash
# ==============================================================================
#   LabelImg2 - Clean Uninstaller for Linux
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
APPS_DIR="$HOME/.local/share/applications"
BIN_DIR="$HOME/.local/bin"

echo "=============================================================================="
echo "                   LabelImg2 - Linux Uninstaller"
echo "=============================================================================="
echo ""

# 1. Remove Desktop Shortcut
if [ -f "$DESKTOP_DIR/LabelImg2.desktop" ]; then
    rm -f "$DESKTOP_DIR/LabelImg2.desktop"
    echo "[OK] Removed Desktop shortcut: $DESKTOP_DIR/LabelImg2.desktop"
fi

# 2. Remove Application Menu Entry
if [ -f "$APPS_DIR/labelimg2.desktop" ]; then
    rm -f "$APPS_DIR/labelimg2.desktop"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$APPS_DIR" 2>/dev/null || true
    fi
    echo "[OK] Removed Application menu entry: $APPS_DIR/labelimg2.desktop"
fi

# 3. Remove command wrapper in ~/.local/bin
if [ -f "$BIN_DIR/labelimg2" ]; then
    rm -f "$BIN_DIR/labelimg2"
    echo "[OK] Removed CLI command: $BIN_DIR/labelimg2"
fi

# 4. Optional: Remove virtual environment
if [ -d "$SCRIPT_DIR/.venv" ]; then
    read -p "Do you want to delete the local virtual environment (.venv)? [y/N]: " choice
    case "$choice" in
        y|Y|yes|YES)
            rm -rf "$SCRIPT_DIR/.venv"
            echo "[OK] Removed local virtual environment: $SCRIPT_DIR/.venv"
            ;;
        *)
            echo "[INFO] Kept local virtual environment."
            ;;
    esac
fi

echo ""
echo "[OK] LabelImg2 system integration has been completely removed."
