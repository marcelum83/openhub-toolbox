#!/usr/bin/env bash
# OpenHub Desktop Quick-Start Script
cd "$(dirname "$0")"

# Check virtualenv in VortexIDE or local
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "/home/mike/Documents/main/MicroProjects/VortexIDE/.venv" ]; then
    source /home/mike/Documents/main/MicroProjects/VortexIDE/.venv/bin/activate
elif [ -d "/home/mike/Documents/main/ACE/.venv" ]; then
    source /home/mike/Documents/main/ACE/.venv/bin/activate
fi

python main.py
