"""Gunicorn production configuration."""

import multiprocessing

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2

# Networking
bind = "0.0.0.0:8000"
timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
