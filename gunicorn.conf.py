"""Hardened Gunicorn production WSGI configuration."""

import multiprocessing
import os

# Bind address and port
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '5000')}"

# Worker processes and threads
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", "4"))

# Timeouts and keep-alive
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 30
keepalive = 5

# Worker recycling to prevent memory leaks over long uptimes
max_requests = 1000
max_requests_jitter = 100

# HTTP request line and header size limits (DoS / buffer overflow protection)
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Logging to stdout/stderr for container & cloud log aggregators
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
capture_output = True
