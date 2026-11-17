#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
speako_python=".venv/bin/python"
if [ ! -x "$speako_python" ]; then
    echo 'Run the setup first: bash setup.sh'
    exit 1
fi
"$speako_python" manage.py migrate --noinput
echo 'Speako runs locally at http://127.0.0.1:8001/ . Keep this window open; Ctrl+C stops it.'
exec "$speako_python" manage.py runserver 127.0.0.1:8001 --insecure --noreload
