.PHONY: all start stop restart status clean install help
.PHONY: start-cap start-pro start-ret stop-cap stop-pro stop-ret

# Default target
all: help

# ============================================================
# MAIN COMMANDS
# ============================================================

# Start entire Blueberry system
start: start-pro start-cap start-ret
	@echo ""
	@echo "════════════════════════════════════════════════════════"
	@echo "  🫐 BLUEBERRY VOICE ASSISTANT - ALL SERVICES RUNNING"
	@echo "════════════════════════════════════════════════════════"
	@echo ""
	@$(MAKE) --no-print-directory status

# Stop entire system
stop: stop-ret stop-cap stop-pro
	@echo "✓ All Blueberry services stopped"

# Restart entire system
restart: stop
	@sleep 2
	@$(MAKE) --no-print-directory start

# Check status of all services
status:
	@echo "📊 Service Status:"
	@echo ""
	@echo "AUD_PRO (Processing):"
	@pgrep -f "rasa run$$" > /dev/null && echo "  ✓ Rasa Server: Running" || echo "  ✗ Rasa Server: Stopped"
	@pgrep -f "rasa run actions" > /dev/null && echo "  ✓ Rasa Actions: Running" || echo "  ✗ Rasa Actions: Stopped"
	@pgrep -f "rasa_bridge.py" > /dev/null && echo "  ✓ Rasa Bridge: Running" || echo "  ✗ Rasa Bridge: Stopped"
	@pgrep -f "time_parser.py" > /dev/null && echo "  ✓ Time Parser: Running" || echo "  ✗ Time Parser: Stopped"
	@pgrep -f "time_daemon.py" > /dev/null && echo "  ✓ Time Daemon: Running" || echo "  ✗ Time Daemon: Stopped"
	@echo ""
	@echo "AUD_CAP (Capture):"
	@pgrep -f "AUD_CAP/main.py" > /dev/null && echo "  ✓ Audio Capture: Running" || echo "  ✗ Audio Capture: Stopped"
	@echo ""
	@echo "AUD_RET (Output):"
	@pgrep -f "AUD_RET/output.py" > /dev/null && echo "  ✓ Audio Output: Running" || echo "  ✗ Audio Output: Stopped"
	@echo ""

# ============================================================
# AUD_PRO: PROCESSING SERVICES
# ============================================================

start-pro:
	@echo "🔧 Starting AUD_PRO (Processing Services)..."
	@cd AUD_PRO && nohup rasa run --enable-api --port 5005 > logs/rasa_server.log 2>&1 & echo $$! > /tmp/blueberry_rasa_server.pid
	@sleep 3
	@cd AUD_PRO && nohup rasa run actions --port 5055 > logs/rasa_actions.log 2>&1 & echo $$! > /tmp/blueberry_rasa_actions.pid
	@sleep 2
	@cd AUD_PRO && nohup py rasa_bridge.py > logs/rasa_bridge.log 2>&1 & echo $$! > /tmp/blueberry_rasa_bridge.pid
	@sleep 1
	@cd AUD_PRO/services && nohup py time_parser.py > ../logs/time_parser.log 2>&1 & echo $$! > /tmp/blueberry_time_parser.pid
	@sleep 1
	@cd AUD_PRO && nohup py time_daemon.py > ../logs/time_daemon.log 2>&1 & echo $$! > /tmp/blueberry_time_daemon.pid
	@sleep 2
	@echo "  ✓ AUD_PRO services started"

stop-pro:
	@echo "🛑 Stopping AUD_PRO..."
	@-pkill -f "rasa run$$" 2>/dev/null || true
	@-pkill -f "rasa run actions" 2>/dev/null || true
	@-pkill -f "rasa_bridge.py" 2>/dev/null || true
	@-pkill -f "time_parser.py" 2>/dev/null || true
	@-pkill -f "time_daemon.py" 2>/dev/null || true
	@-rm -f /tmp/blueberry_rasa_*.pid /tmp/blueberry_time_*.pid 2>/dev/null || true
	@echo "  ✓ AUD_PRO stopped"

# ============================================================
# AUD_CAP: AUDIO CAPTURE (Wake Word + MQTT)
# ============================================================

start-cap:
	@echo "🎤 Starting AUD_CAP (Audio Capture)..."
	@cd AUD_CAP && nohup py main.py > logs/audio_capture.log 2>&1 & echo $$! > /tmp/blueberry_audio_cap.pid
	@sleep 2
	@echo "  ✓ AUD_CAP started (listening for 'Blueberry')"

stop-cap:
	@echo "🛑 Stopping AUD_CAP..."
	@-pkill -f "AUD_CAP/main.py" 2>/dev/null || true
	@-rm -f /tmp/blueberry_audio_cap.pid 2>/dev/null || true
	@echo "  ✓ AUD_CAP stopped"

# ============================================================
# AUD_RET: AUDIO OUTPUT (TTS)
# ============================================================

start-ret:
	@echo "🔊 Starting AUD_RET (Audio Output)..."
	@cd AUD_RET && nohup py output.py > logs/audio_output.log 2>&1 & echo $$! > /tmp/blueberry_audio_ret.pid
	@sleep 1
	@echo "  ✓ AUD_RET started"

stop-ret:
	@echo "🛑 Stopping AUD_RET..."
	@-pkill -f "AUD_RET/output.py" 2>/dev/null || true
	@-rm -f /tmp/blueberry_audio_ret.pid 2>/dev/null || true
	@echo "  ✓ AUD_RET stopped"

# ============================================================
# UTILITY COMMANDS
# ============================================================

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@pip install -r requirements_current.txt
	@echo "✓ Dependencies installed"

# Create log directories
setup-logs:
	@mkdir -p AUD_CAP/logs AUD_PRO/logs AUD_RET/logs
	@echo "✓ Log directories created"

# Clean logs and temp files
clean:
	@echo "🧹 Cleaning temporary files..."
	@rm -rf AUD_CAP/logs/*.log AUD_PRO/logs/*.log AUD_RET/logs/*.log
	@rm -rf AUD_RET/tts_cache/*.wav
	@rm -rf **/__pycache__ **/**/__pycache__
	@rm -f /tmp/blueberry_*.pid
	@echo "✓ Cleaned"

# View logs
logs-cap:
	@tail -f AUD_CAP/logs/audio_capture.log

logs-pro:
	@echo "Select log:"
	@echo "  1) Rasa Server"
	@echo "  2) Rasa Actions"
	@echo "  3) Rasa Bridge"
	@echo "  4) Time Parser"
	@echo "  5) Time Daemon"
	@read -p "Choice: " choice; \
	case $$choice in \
		1) tail -f AUD_PRO/logs/rasa_server.log ;; \
		2) tail -f AUD_PRO/logs/rasa_actions.log ;; \
		3) tail -f AUD_PRO/logs/rasa_bridge.log ;; \
		4) tail -f AUD_PRO/logs/time_parser.log ;; \
		5) tail -f AUD_PRO/logs/time_daemon.log ;; \
		*) echo "Invalid choice" ;; \
	esac

logs-ret:
	@tail -f AUD_RET/logs/audio_output.log

# Test individual components
test-cap:
	@echo "🧪 Testing AUD_CAP..."
	@cd AUD_CAP && python -c "import main; print('✓ AUD_CAP imports OK')"

test-pro:
	@echo "🧪 Testing AUD_PRO..."
	@cd AUD_PRO && rasa --version
	@cd AUD_PRO/services && python -c "import time_parser; print('✓ Time Parser imports OK')"
	@cd AUD_PRO/services && python -c "import time_daemon; print('✓ Time Daemon imports OK')"

test-ret:
	@echo "🧪 Testing AUD_RET..."
	@cd AUD_RET && python -c "import output; print('✓ AUD_RET imports OK')"

test: test-cap test-pro test-ret
	@echo "✓ All components test OK"

# ============================================================
# DEVELOPMENT HELPERS
# ============================================================

# Restart just one module
restart-cap: stop-cap start-cap
restart-pro: stop-pro start-pro
restart-ret: stop-ret start-ret

# Quick check if anything is running
ps:
	@ps aux | grep -E "main.py|rasa|output.py|time_parser|time_daemon|rasa_bridge" | grep -v grep || echo "No Blueberry processes running"

# Kill everything forcefully
kill:
	@echo "💀 Force killing all processes..."
	@-pkill -9 -f "AUD_CAP/main.py" 2>/dev/null || true
	@-pkill -9 -f "AUD_RET/output.py" 2>/dev/null || true
	@-pkill -9 -f "rasa" 2>/dev/null || true
	@-pkill -9 -f "rasa_bridge" 2>/dev/null || true
	@-pkill -9 -f "time_parser" 2>/dev/null || true
	@-pkill -9 -f "time_daemon" 2>/dev/null || true
	@rm -f /tmp/blueberry_*.pid
	@echo "✓ Force killed all processes"

# ============================================================
# HELP
# ============================================================

help:
	@echo ""
	@echo "════════════════════════════════════════════════════════"
	@echo "  🫐 BLUEBERRY VOICE ASSISTANT - Makefile Commands"
	@echo "════════════════════════════════════════════════════════"
	@echo ""
	@echo "Main Commands:"
	@echo "  make start          Start entire Blueberry system"
	@echo "  make stop           Stop entire system"
	@echo "  make restart        Restart entire system"
	@echo "  make status         Check status of all services"
	@echo ""
	@echo "Module Commands:"
	@echo "  make start-cap      Start AUD_CAP (audio capture)"
	@echo "  make start-pro      Start AUD_PRO (processing)"
	@echo "  make start-ret      Start AUD_RET (audio output)"
	@echo "  make restart-cap    Restart AUD_CAP only"
	@echo "  make restart-pro    Restart AUD_PRO only"
	@echo "  make restart-ret    Restart AUD_RET only"
	@echo ""
	@echo "Logs:"
	@echo "  make logs-cap       View AUD_CAP logs"
	@echo "  make logs-pro       View AUD_PRO logs (interactive)"
	@echo "  make logs-ret       View AUD_RET logs"
	@echo ""
	@echo "Utilities:"
	@echo "  make install        Install Python dependencies"
	@echo "  make setup-logs     Create log directories"
	@echo "  make clean          Clean logs and temp files"
	@echo "  make test           Test all components"
	@echo "  make ps             Show running Blueberry processes"
	@echo "  make kill           Force kill all processes"
	@echo ""
	@echo "════════════════════════════════════════════════════════"
	@echo ""