#!/bin/zsh
# Double-click this file in Finder to start the Vector Format Converter.
cd "$(dirname "$0")/backend"

# If the app is already running, just open the browser.
if curl -s -o /dev/null --max-time 1 http://localhost:8000/api/formats; then
  open http://localhost:8000
  echo "Converter already running — opened http://localhost:8000"
  exit 0
fi

# Open the browser once the server is up, then start the server.
( for i in {1..30}; do
    sleep 0.5
    curl -s -o /dev/null --max-time 1 http://localhost:8000/api/formats && { open http://localhost:8000; break; }
  done ) &

echo "Starting Vector Format Converter at http://localhost:8000 (close this window or press Ctrl+C to stop)"
exec .venv/bin/uvicorn main:app --port 8000
