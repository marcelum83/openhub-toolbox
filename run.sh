#!/usr/bin/env bash
# OpenHub Desktop Quick-Start Script
cd "$(dirname "$0")"

# Locate Python environment with Kivy & KivyMD
if [ -f "./.venv/bin/python" ]; then
    PYTHON_EXEC="./.venv/bin/python"
elif [ -f "/home/mike/Documents/main/MicroProjects/VortexIDE/.venv/bin/python" ]; then
    PYTHON_EXEC="/home/mike/Documents/main/MicroProjects/VortexIDE/.venv/bin/python"
elif [ -f "/home/mike/Documents/main/.venv/bin/python" ]; then
    PYTHON_EXEC="/home/mike/Documents/main/.venv/bin/python"
else
    PYTHON_EXEC="python3"
fi

"$PYTHON_EXEC" main.py
