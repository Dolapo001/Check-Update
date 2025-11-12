import multiprocessing

# Worker configuration
workers = 2
worker_class = "sync"
timeout = 120
keepalive = 2

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Logging
accesslog = "-"
errorlog = "-"
