# OLD (doesn't support WebSockets):
# web: gunicorn -w 1 --timeout 120 app:app

# NEW (supports WebSockets):
web: gunicorn -w 1 --timeout 120 -k eventlet app:app
