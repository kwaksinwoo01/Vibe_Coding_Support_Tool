#!/usr/bin/env bash
set -euo pipefail
unset PYTHONHOME PYTHONPATH

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repository_root"

required_version="$(tr -d '[:space:]' < .python-version)"
venv_python="$repository_root/.venv/bin/python"

python_version() {
    "$1" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null
}

if [[ ! -x "$venv_python" ]] || [[ "$(python_version "$venv_python" || true)" != "$required_version" ]]; then
    base_python=""
    for candidate in python3.14 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && \
            [[ "$(python_version "$candidate" || true)" == "$required_version" ]]; then
            base_python="$candidate"
            break
        fi
    done

    if [[ -z "$base_python" ]]; then
        echo "Python $required_version is required." >&2
        exit 1
    fi
    if [[ -d "$repository_root/.venv" ]]; then
        echo "Existing .venv is not Python $required_version; remove it explicitly and rerun." >&2
        exit 1
    fi
    "$base_python" -m venv "$repository_root/.venv"
fi

"$venv_python" -m pip install --upgrade pip
"$venv_python" -m pip install -r requirements.txt
"$venv_python" -m PyInstaller vibeStation.spec

echo "Build successful: dist/vibeStation"
