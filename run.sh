#!/usr/bin/env bash
set -e
pip install -r requirements.txt
python src/generate_data.py
python src/analysis.py
python src/flow_diagram.py
