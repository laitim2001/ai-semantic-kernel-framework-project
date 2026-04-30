"""Gunicorn configuration file for production deployment.

Usage:
    # Production (multi-worker)
    SERVER_ENV=production gunicorn main:app -c gunicorn.conf.py

    # Staging (multi-worker, access logs)
    SERVER_ENV=staging gunicorn main:app -c gunicorn.conf.py

Note:
    Gunicorn is NOT used in development. Use uvicorn directly:
    SERVER_ENV=development python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

Sprint 117 — Multi-Worker Uvicorn Configuration
"""

from src.core.server_config import ServerConfig

config = ServerConfig()

# Server socket
bind = config.bind

# Worker processes
workers = config.workers
worker_class = config.worker_class

# Hot-reload (development only, should not be used with Gunicorn)
reload = config.reload

# Logging
loglevel = config.log_level
accesslog = "-" if config.access_log else None
errorlog = "-"

# Timeout
timeout = 120
graceful_timeout = 30
keepalive = 5

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Process naming
proc_name = "ipa-platform"

# Preload app for better memory usage in multi-worker mode
preload_app = not config.reload
