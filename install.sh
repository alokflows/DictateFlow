#!/usr/bin/env bash
# DictateFlow installer — run once: bash install.sh
set -e

echo "==> Installing system dependencies..."
sudo apt-get install -y ffmpeg libxcb-cursor0 libnotify-bin xdotool

echo "==> Installing Python dependencies..."
pip3 install --user --break-system-packages -r requirements.txt

echo "==> Installing launcher..."
mkdir -p ~/.local/bin
cp launcher.sh ~/.local/bin/dictateflow
chmod +x ~/.local/bin/dictateflow

echo "==> Installing systemd user service..."
mkdir -p ~/.config/systemd/user
cp dictateflow.service ~/.config/systemd/user/dictateflow.service
sed -i "s|HOME_DIR|$HOME|g; s|USER_NAME|$USER|g" \
    ~/.config/systemd/user/dictateflow.service

AUTH=$(ls /run/user/$(id -u)/gdm/Xauthority 2>/dev/null \
     || ls /run/user/$(id -u)/.mutter-Xwaylandauth.* 2>/dev/null \
     || echo "$HOME/.Xauthority")
sed -i "s|XAUTH_PATH|$AUTH|g" ~/.config/systemd/user/dictateflow.service

systemctl --user daemon-reload
systemctl --user enable --now dictateflow.service

echo ""
echo "✓ DictateFlow installed and running!"
echo "  Hold Caps Lock to dictate anywhere."
echo "  Right-click the tray icon for settings."
