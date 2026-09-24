#!/usr/bin/env bash
# ==============================================================================
#   LabelImg2 - Create Desktop Shortcut & Application Menu Entry for Linux
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICON_PATH="$SCRIPT_DIR/img/app.png"
if [ ! -f "$ICON_PATH" ]; then
    ICON_PATH="$SCRIPT_DIR/img/labelImg2.png"
fi

START_SCRIPT="$SCRIPT_DIR/Start_LabelImg2.sh"
chmod +x "$START_SCRIPT"

DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"

DESKTOP_FILE="$APPS_DIR/labelimg2.desktop"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=LabelImg2
GenericName=Image Annotation Tool
Comment=Next-Gen Image Annotation and YOLO Training Workbench
Exec="$START_SCRIPT" %F
Icon=$ICON_PATH
Terminal=false
Categories=Development;Graphics;Science;
Keywords=image;annotation;yolo;labeling;cv;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"

# Also copy to ~/Desktop if Desktop directory exists
if [ -d "$DESKTOP_DIR" ]; then
    cp "$DESKTOP_FILE" "$DESKTOP_DIR/LabelImg2.desktop"
    chmod +x "$DESKTOP_DIR/LabelImg2.desktop"
    # Mark as trusted on GNOME / Ubuntu if gio command is available
    if command -v gio >/dev/null 2>&1; then
        gio set "$DESKTOP_DIR/LabelImg2.desktop" metadata::trusted true 2>/dev/null || true
    fi
    echo -e "\033[1;32m[OK] Created Desktop shortcut at: $DESKTOP_DIR/LabelImg2.desktop\033[0m"
fi

# Update desktop application database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

echo -e "\033[1;32m[OK] Created Application Menu entry at: $DESKTOP_FILE\033[0m"
