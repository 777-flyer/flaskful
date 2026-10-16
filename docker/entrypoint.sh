#!/bin/sh
set -e

echo "[FlaskFul] Initializing database tables..."
flask init-db

echo "[FlaskFul] Starting Gunicorn production server..."
exec gunicorn -c gunicorn.conf.py wsgi:app
