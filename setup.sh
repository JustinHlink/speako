#!/usr/bin/env bash
# One-step setup for macOS and Linux. Run from the speako folder: bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"

python_ok() {
    "$1" -c 'import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)' >/dev/null 2>&1
}

if [ ! -x .venv/bin/python ]; then
    echo 'Looking for Python 3.10 to 3.13 ...'
    py=''
    for candidate in python3.12 python3.13 python3.11 python3.10 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && python_ok "$candidate"; then
            py="$candidate"
            break
        fi
    done
    if [ -z "$py" ]; then
        echo 'Setup stopped: Python 3.10 to 3.13 was not found.'
        echo '  macOS: install Python 3.12 from https://www.python.org/downloads/ (or: brew install python@3.12)'
        echo '  Ubuntu or Debian: sudo apt install python3.12 python3.12-venv'
        echo 'Then run: bash setup.sh'
        exit 1
    fi
    echo "Using $("$py" --version). Creating the virtual environment .venv ..."
    if ! "$py" -m venv .venv; then
        rm -rf .venv
        echo 'Setup stopped: Python could not create .venv.'
        echo '  Ubuntu or Debian: sudo apt install python3-venv (or python3.12-venv), then run: bash setup.sh'
        exit 1
    fi
fi

exec .venv/bin/python setup_local.py
