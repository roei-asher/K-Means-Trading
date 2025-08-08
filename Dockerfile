# K-Means Trading Strategy Docker Container
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ src/
COPY config.yaml .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash kmeans
RUN chown -R kmeans:kmeans /app
USER kmeans

# Expose WebSocket port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import websockets; import asyncio; asyncio.run(websockets.connect('ws://localhost:8765'))" || exit 1

# Default command
CMD ["python", "src/server.py"]