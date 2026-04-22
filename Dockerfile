FROM python:3.11-slim

# Create non-root user for sandboxed execution
RUN useradd -m -u 1000 agent

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn[standard] sse-starlette

# Copy project
COPY . .

# Pre-create logs directory with correct permissions
RUN mkdir -p /app/logs && chown -R agent:agent /app

# Switch to non-root user
USER agent

EXPOSE 8000

# Default: run the web UI
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
