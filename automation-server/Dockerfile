FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

WORKDIR /app

# Install uv
RUN pip install uv

# Xvfb ships with this base image already. Add a VNC server (x11vnc) and a
# browser-based VNC client (novnc + websockify) so a headed (non-headless)
# scrape can be watched live from a browser tab, even though this container
# has no real display.
RUN apt-get update && apt-get install -y --no-install-recommends \
    x11vnc novnc websockify \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
# --frozen ensures we use the exact versions from uv.lock
RUN uv sync --frozen

# Copy the rest of the application
COPY . .
RUN chmod +x docker/entrypoint.sh

# Expose the application port and the noVNC live-view port
EXPOSE 8000 6080

ENTRYPOINT ["docker/entrypoint.sh"]
