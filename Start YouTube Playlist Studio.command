#!/bin/zsh
# Double-click this file in Finder to start the local dashboard.
set -euo pipefail

PROJECT_DIR="/Users/rezafarzin/Documents/ChatGPT/youtube_playlist_studio"
PORT="${YPS_PORT:-8787}"

cd "$PROJECT_DIR"
mkdir -p logs

# Optional local secrets/configuration. This file is ignored by Git.
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

if [[ ! -x .venv/bin/python3 ]]; then
  echo "Creating Python virtual environment…"
  python3 -m venv .venv
fi

PYTHON_BIN="$PROJECT_DIR/.venv/bin/python3"
"$PYTHON_BIN" -m pip install --disable-pip-version-check -q -r requirements.txt

for tool in yt-dlp ffmpeg ffprobe; do
  command -v "$tool" >/dev/null || {
    echo "Missing required tool: $tool"
    echo "Install it with: brew install yt-dlp ffmpeg"
    read "?Press Enter to close…"
    exit 1
  }
done

# If an existing Studio instance is already healthy, simply show it.
if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
  open "http://127.0.0.1:${PORT}"
  exit 0
fi

echo "Starting YouTube Playlist Studio…"
"$PYTHON_BIN" app.py > logs/launcher.log 2>&1 &
SERVER_PID=$!
cleanup() { kill "$SERVER_PID" 2>/dev/null || true; }
trap cleanup INT TERM EXIT

for attempt in {1..30}; do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    open "http://127.0.0.1:${PORT}"
    echo "Dashboard is running. Keep this Terminal window open."
    wait "$SERVER_PID"
    exit $?
  fi
  sleep 1
done

echo "Dashboard did not start. See: $PROJECT_DIR/logs/launcher.log"
wait "$SERVER_PID" || true
read "?Press Enter to close…"
