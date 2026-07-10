#!/bin/sh
set -e

Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &
export DISPLAY=:99

# Give Xvfb a moment to be ready before X clients attach
sleep 1

if [ -n "$VNC_PASSWORD" ]; then
  x11vnc -display :99 -forever -shared -rfbport 5900 -passwd "$VNC_PASSWORD" -quiet &
else
  echo "⚠️  VNC_PASSWORD not set — live view VNC server has no password. Don't expose port 6080 beyond your own machine."
  x11vnc -display :99 -forever -shared -rfbport 5900 -nopw -quiet &
fi

websockify --web=/usr/share/novnc 6080 localhost:5900 &

exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
