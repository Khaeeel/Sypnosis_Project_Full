#!/bin/bash

# This automatically finds the root folder where this script is sitting
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🤖 Starting Viber Master Bot from $DIR..."

# SAFETY FEATURE
cleanup() {
    echo ""
    echo "🛑 Stopping all Viber bots..."
    kill $(jobs -p) 2>/dev/null
    echo "✅ All bots shut down safely."
    exit 0
}
trap cleanup SIGINT SIGTERM

# ==========================================
# 1. RUN AUTO-CAPTURE (Python)
# ==========================================
echo "📸 Starting Auto-Capture..."
"$DIR/.venv/bin/python" "$DIR/watcher/auto_capture.py" &

# ==========================================
# 2. RUN AUTO-SCROLL (Python)
# ==========================================
echo "📜 Starting Auto-Scroll..."
"$DIR/.venv/bin/python" "$DIR/watcher/auto_scroll.py" &

# ==========================================
# 3. RUN CALL CANCELER (Python Visual Bot)
# ==========================================
echo "🚫 Starting Visual Call Canceler..."
"$DIR/.venv/bin/python" "$DIR/watcher/visual_call_blocker.py" &

echo "=========================================="
echo "✅ All 3 bots are now running in the background!"
echo "⚠️  Press CTRL+C in this terminal to stop everything."
echo "=========================================="

# Keep the master script alive
wait