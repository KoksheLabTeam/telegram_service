#!/bin/sh
echo "Applying migrations..."
alembic upgrade head
echo "Starting bot..."
exec python app/main.py