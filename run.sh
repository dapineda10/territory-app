#!/bin/bash
set -e

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    py -3.11 -m venv "$VENV_DIR"
    "$VENV_DIR/Scripts/pip" install --upgrade pip --quiet
    "$VENV_DIR/Scripts/pip" install \
        "streamlit==1.44.1" \
        "folium==0.20.0" \
        "streamlit-folium==0.27.1" \
        "shapely==2.1.2" \
        "bcrypt>=4.0"
    echo "Dependencies installed."
fi

echo "Starting app..."
"$VENV_DIR/Scripts/streamlit" run app.py --browser.gatherUsageStats=false
