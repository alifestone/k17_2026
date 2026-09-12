#!/bin/sh
set -eu

mkdir -p /app/data/configs /app/data/runtime /app/data/output
python /app/worker.py init
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 30 app:app
