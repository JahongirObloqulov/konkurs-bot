#!/usr/bin/env bash
# Telegram bot + Web admin panelni birga ishga tushirish
set -e

echo "==> Telegram bot ishga tushmoqda (background)..."
python bot.py &
BOT_PID=$!
echo "  Bot PID: $BOT_PID"

echo "==> Web admin panel ishga tushmoqda..."
exec gunicorn web.app:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -