#!/usr/bin/env bash
# Samsung Frame Manager — Linux/Mac start script
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating venv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing backend deps..."
pip install --upgrade pip >/dev/null
pip install -r backend/requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from template — edit and re-run if needed."
fi

# Load nvm if available (Linux/Mac, no system Node installed)
if ! command -v node >/dev/null 2>&1; then
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  # shellcheck disable=SC1091
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
fi

if command -v node >/dev/null 2>&1; then
  if [ ! -d frontend/dist ]; then
    echo "Building frontend..."
    (cd frontend && npm install && npm run build)
  fi
else
  echo "Node.js not found — frontend will not be served. API only."
  echo "  Install Node.js or nvm to enable the UI: https://github.com/nvm-sh/nvm"
fi

echo "Starting Frame Manager on http://localhost:8000"
exec python -m backend.main
