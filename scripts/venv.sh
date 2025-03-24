#!/usr/bin/env bash

# create the python virtual environment
python3 -m venv .venv
pip install uv

# activate it
source .venv/bin/activate
