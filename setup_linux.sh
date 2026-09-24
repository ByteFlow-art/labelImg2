#!/usr/bin/env bash
# ==============================================================================
#   LabelImg2 - Automated Environment Setup Wizard for Linux
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

AUTO_MODE=0
for arg in "$@"; do
    if [ "$arg" = "--auto" ] || [ "$arg" = "-y" ]; then
        AUTO_MODE=1
    fi
done

echo -e "${BLUE}${BOLD}==============================================================================${NC}"
echo -e "${BLUE}${BOLD}             LabelImg2 Next-Gen - Linux Environment Setup Wizard${NC}"
echo -e "${BLUE}${BOLD}==============================================================================${NC}"
echo ""

# Ensure helper scripts have executable bit
chmod +x "$SCRIPT_DIR/Start_LabelImg2.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/Create_Desktop_Shortcut.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/Uninstall_LabelImg2.sh" 2>/dev/null || true

# ------------------------------------------------------------------------------
# Step 1: Detect Linux Distribution and System Dependencies
# ------------------------------------------------------------------------------
echo -e "${BOLD}[Step 1/5] Checking Linux system dependencies...${NC}"

DISTRO=""
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
fi

# Detect common package managers and suggest missing GUI libraries
check_system_package() {
    local pkg_name="$1"
    if command -v dpkg >/dev/null 2>&1; then
        dpkg -s "$pkg_name" >/dev/null 2>&1
    elif command -v rpm >/dev/null 2>&1; then
        rpm -q "$pkg_name" >/dev/null 2>&1
    else
        return 0
    fi
}

MISSING_SYS_PKGS=()
if [ "$DISTRO" = "ubuntu" ] || [ "$DISTRO" = "debian" ] || [ "$DISTRO" = "linuxmint" ] || [ "$DISTRO" = "deepin" ]; then
    for pkg in libgl1 libglib2.0-0 libxcb-xinerama0 python3-venv python3-pip; do
        if ! check_system_package "$pkg"; then
            MISSING_SYS_PKGS+=("$pkg")
        fi
    done
elif [ "$DISTRO" = "fedora" ] || [ "$DISTRO" = "rhel" ] || [ "$DISTRO" = "centos" ]; then
    for pkg in mesa-libGL glib2 python3-pip; do
        if ! check_system_package "$pkg"; then
            MISSING_SYS_PKGS+=("$pkg")
        fi
    done
fi

if [ ${#MISSING_SYS_PKGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}[!] Missing recommended system libraries for Qt5 / OpenCV: ${MISSING_SYS_PKGS[*]}${NC}"
    if [ "$AUTO_MODE" -eq 1 ]; then
        if command -v sudo >/dev/null 2>&1; then
            echo -e "${BLUE}[*] Auto-installing missing system libraries via sudo...${NC}"
            if [ "$DISTRO" = "ubuntu" ] || [ "$DISTRO" = "debian" ] || [ "$DISTRO" = "linuxmint" ]; then
                sudo apt-get update -y && sudo apt-get install -y "${MISSING_SYS_PKGS[@]}" || true
            fi
        fi
    else
        echo -e "${YELLOW}    To install them manually, run: sudo apt-get install -y ${MISSING_SYS_PKGS[*]}${NC}"
    fi
else
    echo -e "${GREEN}[OK] Core system GUI libraries are present.${NC}"
fi

# ------------------------------------------------------------------------------
# Step 2: Detect Python / Conda Environment
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}[Step 2/5] Detecting Python / Conda runtime...${NC}"

PYTHON_EXE=""
USE_CONDA=0

# Check existing Conda command
if command -v conda >/dev/null 2>&1; then
    echo -e "${GREEN}[OK] Found Conda package manager.$(conda --version 2>/dev/null || true)${NC}"
    USE_CONDA=1
fi

# Fallback: check conda binary in common installation locations
if [ "$USE_CONDA" -eq 0 ]; then
    for c_dir in "$HOME/miniconda3/bin" "$HOME/anaconda3/bin" "/opt/conda/bin" "/opt/miniconda3/bin"; do
        if [ -x "$c_dir/conda" ]; then
            export PATH="$c_dir:$PATH"
            USE_CONDA=1
            echo -e "${GREEN}[OK] Found Conda in $c_dir.${NC}"
            break
        fi
    done
fi

# ------------------------------------------------------------------------------
# Step 3: Create / Configure Virtual Environment
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}[Step 3/5] Setting up isolated Python environment...${NC}"

VENV_DIR="$SCRIPT_DIR/.venv"

if [ "$USE_CONDA" -eq 1 ]; then
    # Setup Conda environment 'labelimg2'
    CONDA_ENV_NAME="labelimg2"
    if ! conda env list | grep -E "^${CONDA_ENV_NAME}[[:space:]]" >/dev/null 2>&1; then
        echo -e "${BLUE}[*] Creating dedicated Conda environment: $CONDA_ENV_NAME (Python 3.10)...${NC}"
        conda create -n "$CONDA_ENV_NAME" python=3.10 -y
    else
        echo -e "${GREEN}[OK] Reusing existing Conda environment: $CONDA_ENV_NAME.${NC}"
    fi
    CONDA_BASE="$(conda info --base 2>/dev/null || echo "$HOME/miniconda3")"
    PYTHON_EXE="$CONDA_BASE/envs/$CONDA_ENV_NAME/bin/python"
    if [ ! -f "$PYTHON_EXE" ]; then
        PYTHON_EXE="$(conda run -n "$CONDA_ENV_NAME" which python 2>/dev/null || echo "")"
    fi
fi

# If Conda is not available or failed, use standard python3 venv
if [ -z "$PYTHON_EXE" ] || [ ! -f "$PYTHON_EXE" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}[ERROR] Python 3 is not installed on this system!${NC}"
        echo "Please install Python 3 (3.8 ~ 3.12): sudo apt-get install -y python3 python3-venv python3-pip"
        exit 1
    fi

    PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    echo -e "${GREEN}[OK] Found system Python: $PY_VER ($(which python3))${NC}"

    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${BLUE}[*] Creating local virtual environment at: $VENV_DIR ...${NC}"
        python3 -m venv "$VENV_DIR" || {
            echo -e "${RED}[ERROR] Failed to create virtual environment.${NC}"
            echo "Please run: sudo apt-get install -y python3-venv"
            exit 1
        }
    else
        echo -e "${GREEN}[OK] Found existing local virtual environment: $VENV_DIR.${NC}"
    fi
    PYTHON_EXE="$VENV_DIR/bin/python"
fi

echo -e "${GREEN}[OK] Target Python interpreter: $PYTHON_EXE${NC}"

# ------------------------------------------------------------------------------
# Step 4: Install Dependencies from requirements.txt
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}[Step 4/5] Installing dependencies from requirements.txt...${NC}"

PIP_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple"

# Test connectivity to Tsinghua mirror, fallback to official PyPI if outside China
if ! curl --connect-timeout 2 -s "$PIP_INDEX" >/dev/null 2>&1; then
    PIP_INDEX="https://pypi.org/simple"
    echo -e "${BLUE}[INFO] Using official PyPI index ($PIP_INDEX)...${NC}"
else
    echo -e "${BLUE}[INFO] Using high-speed Tsinghua PyPI mirror ($PIP_INDEX)...${NC}"
fi

"$PYTHON_EXE" -m pip install --upgrade pip -i "$PIP_INDEX" --trusted-host "$(echo "$PIP_INDEX" | awk -F[/:] '{print $4}')" || true

echo -e "${BLUE}[*] Installing requirements (PyQt5, Ultralytics, OpenCV, Torch)...${NC}"
"$PYTHON_EXE" -m pip install -r "$SCRIPT_DIR/requirements.txt" \
    -i "$PIP_INDEX" \
    --trusted-host "$(echo "$PIP_INDEX" | awk -F[/:] '{print $4}')"

# Verify core dependencies
echo ""
echo -e "${BLUE}[*] Verifying installed packages...${NC}"
"$PYTHON_EXE" -c "
import PyQt5, cv2, torch, ultralytics
print(f'  [OK] PyQt5: {PyQt5.__file__}')
print(f'  [OK] OpenCV: {cv2.__version__}')
print(f'  [OK] PyTorch: {torch.__version__} (CUDA available: {torch.cuda.is_available()})')
print(f'  [OK] Ultralytics: {ultralytics.__version__}')
" || {
    echo -e "${YELLOW}[WARNING] Some dependencies had warnings during verification, but continuing...${NC}"
}

# ------------------------------------------------------------------------------
# Step 5: Create Desktop Shortcut & Global Command Wrapper
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}[Step 5/5] Creating Desktop Entry & CLI integration...${NC}"

# Create Desktop Shortcut
bash "$SCRIPT_DIR/Create_Desktop_Shortcut.sh"

# Create CLI command wrapper in ~/.local/bin/labelimg2
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
cat <<EOF > "$BIN_DIR/labelimg2"
#!/usr/bin/env bash
exec "$SCRIPT_DIR/Start_LabelImg2.sh" "\$@"
EOF
chmod +x "$BIN_DIR/labelimg2"
echo -e "${GREEN}[OK] Global CLI command created at: $BIN_DIR/labelimg2${NC}"

# ------------------------------------------------------------------------------
# Finish
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}==============================================================================${NC}"
echo -e "${GREEN}${BOLD}           [SUCCESS] LabelImg2 Linux Setup Completed Successfully!            ${NC}"
echo -e "${GREEN}${BOLD}==============================================================================${NC}"
echo ""
echo -e "You can launch LabelImg2 in any of the following ways:"
echo -e "  1. Direct Launcher : ${BOLD}./Start_LabelImg2.sh${NC}"
echo -e "  2. Terminal Command: ${BOLD}labelimg2${NC} (ensure ~/.local/bin is in your PATH)"
echo -e "  3. Desktop App Menu: Search ${BOLD}LabelImg2${NC} in your system Applications menu"
echo ""

if [ "$AUTO_MODE" -eq 0 ]; then
    read -p "Would you like to launch LabelImg2 now? [Y/n]: " run_choice
    case "$run_choice" in
        n|N|no|NO)
            echo "Done. Have fun annotating!"
            ;;
        *)
            echo "Starting LabelImg2..."
            exec "$SCRIPT_DIR/Start_LabelImg2.sh"
            ;;
    esac
fi
