#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
speako_python=".venv/bin/python"
if [ ! -x "$speako_python" ]; then
    echo 'Create the virtual environment first: python3 -m venv .venv'
    echo 'Then install dependencies: .venv/bin/python -m pip install -r requirements.txt'
    exit 1
fi
"$speako_python" manage.py migrate --noinput
echo 'Speako runs locally at http://127.0.0.1:8001/ . Keep this window open; Ctrl+C stops it.'
exec "$speako_python" manage.py runserver 127.0.0.1:8001 --insecure --noreload
