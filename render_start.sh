#!/bin/bash
python3 setup_database.py
gunicorn app:app --bind 0.0.0.0:$PORT
