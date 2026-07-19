#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}     JCamera - One-Click Install${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

APP_NAME="jcamera"
INSTALL_DIR="${HOME}/.local/${APP_NAME}"
BIN_DIR="${HOME}/.local/bin"
SHARE_DIR="${HOME}/.local/share"

# Ensure directories exist
mkdir -p "${INSTALL_DIR}"
mkdir -p "${BIN_DIR}"
mkdir -p "${SHARE_DIR}/applications"

# Icon goes alongside the app (avoids root-owned icon dirs)
ICON_PATH="${INSTALL_DIR}/logo.svg"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${BLUE}[1/5] Installing system dependencies...${NC}"
if command -v apt &>/dev/null; then
    sudo apt install -y ffmpeg v4l-utils pulseaudio-utils python3 python3-pip python3-venv 2>/dev/null || true
elif command -v dnf &>/dev/null; then
    sudo dnf install -y ffmpeg v4l-utils pulseaudio-utils python3 python3-pip 2>/dev/null || true
elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm ffmpeg v4l-utils pulseaudio python python-pip 2>/dev/null || true
else
    echo -e "${RED}Warning: Could not detect package manager. Install ffmpeg & python3 manually.${NC}"
fi

echo -e "${BLUE}[1b/5] Installing PyQt5 system package...${NC}"
sudo apt install -y python3-pyqt5 2>/dev/null || true

echo -e "${BLUE}[2/5] Setting up Python virtual environment...${NC}"
python3 -m venv --system-site-packages "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --quiet opencv-python 2>&1 | tail -1 || true

# Remove conflicting OpenCV Qt platform plugins
rm -rf "${INSTALL_DIR}/venv/lib/python*/site-packages/cv2/qt/plugins" 2>/dev/null || true

echo -e "${BLUE}[3/5] Installing application files...${NC}"
cp -r "${SCRIPT_DIR}/jcamera" "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/jcamera.py" "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/logo.svg" "${INSTALL_DIR}/"

cat > "${BIN_DIR}/${APP_NAME}" << 'PYEOF'
#!/usr/bin/env bash
exec "${HOME}/.local/jcamera/venv/bin/python3" "${HOME}/.local/jcamera/jcamera.py" "$@"
PYEOF
chmod +x "${BIN_DIR}/${APP_NAME}"

echo -e "${BLUE}[4/5] Creating desktop entry...${NC}"
cp "${SCRIPT_DIR}/resources/jcamera.desktop" "${SHARE_DIR}/applications/${APP_NAME}.desktop"
sed -i "s|Exec=jcamera|Exec=${BIN_DIR}/${APP_NAME}|" "${SHARE_DIR}/applications/${APP_NAME}.desktop"
sed -i "s|Icon=jcamera|Icon=${ICON_PATH}|" "${SHARE_DIR}/applications/${APP_NAME}.desktop"

echo -e "${BLUE}[5/5] Updating application cache...${NC}"
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "${SHARE_DIR}/applications" 2>/dev/null || true
fi

# Add to PATH if not already there
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    SHELL_CONFIG="${HOME}/.$(basename "${SHELL}")rc"
    if [ -f "${SHELL_CONFIG}" ]; then
        echo "" >> "${SHELL_CONFIG}"
        echo "# Added by JCamera installer" >> "${SHELL_CONFIG}"
        echo "export PATH=\"\${PATH}:${BIN_DIR}\"" >> "${SHELL_CONFIG}"
        echo -e "${BLUE}Added ${BIN_DIR} to PATH in ${SHELL_CONFIG}${NC}"
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  JCamera installed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Launching JCamera...${NC}"
echo ""

# Run in background so terminal stays usable
export PATH="${PATH}:${BIN_DIR}"
nohup "${BIN_DIR}/${APP_NAME}" >/dev/null 2>&1 &
disown

sleep 1
echo -e "${GREEN}JCamera is now running!${NC}"
echo -e "Launch again anytime with: ${BLUE}jcamera${NC} or from your app menu: ${BLUE}JCamera${NC}"
