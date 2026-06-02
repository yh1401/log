#!/bin/bash

cd "$(dirname "$0")/.."

echo "📊 Starting Log Analyzer Web Server..."
echo "----------------------------------------"
echo ""
echo "Server will be available at:"
echo "  http://localhost:8000"
echo ""
echo "Concurrency Configuration:"
echo "  - Workers: 4 (CPU cores)"
echo "  - Connections: 200 per worker"
echo "  - Target: 50+ QPS"
echo ""
echo "Press Ctrl+C to stop the server"
echo "----------------------------------------"
echo ""

uvicorn web.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --limit-concurrency 200 \
    --backlog 2048 \
    --timeout-keep-alive 30
