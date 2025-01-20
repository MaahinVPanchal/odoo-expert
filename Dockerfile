FROM python:3.10-slim as builder

WORKDIR /app

# Copy only requirements first
COPY requirements.txt .

# Install dependencies in virtual environment
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.10-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    pandoc \
    git \
    cron \
    curl \
    ca-certificates \
    supervisor \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /var/cache/apt/*

# Create directories with proper permissions
RUN mkdir -p raw_data markdown logs /var/log/supervisor && \
    chmod -R 755 logs /var/log/supervisor

# Copy application files
COPY main.py pull_rawdata.sh ./
COPY src/ ./src/
COPY docker/entrypoint.sh ./docker/entrypoint.sh
COPY docker/crontab /etc/cron.d/updater-cron
COPY docker/healthcheck.py ./docker/healthcheck.py
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set up permissions and logging
RUN chmod 0644 /etc/cron.d/updater-cron && \
    crontab /etc/cron.d/updater-cron && \
    chmod +x pull_rawdata.sh && \
    chmod +x docker/entrypoint.sh && \
    chmod +x docker/healthcheck.py && \
    touch /var/log/cron.log && \
    chmod 0666 /var/log/cron.log && \
    mkdir -p /app/logs && \
    touch /app/logs/ui.log /app/logs/api.log /app/logs/updater.log \
          /app/logs/ui-error.log /app/logs/api-error.log /app/logs/updater-error.log && \
    chmod 0666 /app/logs/*.log

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python docker/healthcheck.py

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]