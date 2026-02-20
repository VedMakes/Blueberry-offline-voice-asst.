#!/bin/bash
set -e

echo "Starting Blueberry AUD_PRO services..."

# Start temporal parser in background
cd /app/services
py time_parser.py &
PARSER_PID=$!
echo "Temporal parser started (PID: $PARSER_PID)"

# Start time daemon in background
py time_daemon.py &
DAEMON_PID=$!
echo "Time daemon started (PID: $DAEMON_PID)"

# Go back to app root
cd /app

# Start Rasa actions server in background
rasa run actions --port 5055 &
ACTIONS_PID=$!
echo "Rasa actions server started (PID: $ACTIONS_PID)"

# Give actions server time to start
sleep 5

# Start Rasa NLU server in background
rasa run --enable-api --port 5005 --cors "*" &
RASA_PID=$!
echo "Rasa server started (PID: $RASA_PID)"

# Give Rasa time to start
sleep 5

# Start Rasa bridge (foreground)
py rasa_bridge.py &
BRIDGE_PID=$!
echo "Rasa bridge started (PID: $BRIDGE_PID)"

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?