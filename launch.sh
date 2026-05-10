#!/bin/bash
# Launch the Crossflow Turbine Designer web app.
# Double-click this file in the file manager, or run: bash launch.sh

cd "$(dirname "$0")"
source .venv/bin/activate
echo "Starting Crossflow Turbine Designer..."
echo "Opening in browser at http://localhost:8501"
streamlit run app.py --server.headless false
