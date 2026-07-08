FROM oven/bun:1-slim

WORKDIR /app

# Install dependencies first so this layer is cached across source changes
COPY package.json bun.lock* ./
RUN bun install

# Copy the rest of the application
COPY . .

EXPOSE 3000

# -H 0.0.0.0 so the dev server is reachable from outside the container
CMD ["bunx", "next", "dev", "-H", "0.0.0.0", "-p", "3000"]
