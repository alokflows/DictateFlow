#!/usr/bin/env bash
# Finds the correct Xauthority and launches DictateFlow
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$(ls /run/user/$(id -u)/gdm/Xauthority 2>/dev/null || echo "$HOME/.Xauthority")}"
exec python3 -m dictateflow "$@"
