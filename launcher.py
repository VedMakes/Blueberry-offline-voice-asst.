#!/usr/bin/env python3
"""
Blueberry Voice Assistant Launcher
Manages all services including MQTT broker
"""

import subprocess
import sys
import time
import os
import signal
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

# Fix Windows Unicode encoding for redirected output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ANSI colors (disabled on Windows if no ANSI support)
try:
    import colorama
    colorama.init()
    USE_COLORS = True
except ImportError:
    USE_COLORS = sys.platform != 'win32'

class Colors:
    if USE_COLORS:
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BOLD = '\033[1m'
        END = '\033[0m'
    else:
        BLUE = GREEN = YELLOW = RED = BOLD = END = ''

# Global process registry
processes: List[Tuple[str, subprocess.Popen]] = []

def print_header(text: str):
    """Print colored header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")

def print_success(text: str):
    """Print success message (use * instead of unicode on Windows)"""
    symbol = '*' if sys.platform == 'win32' else '✓'
    print(f"{Colors.GREEN}{symbol} {text}{Colors.END}")

def print_error(text: str):
    """Print error message"""
    symbol = 'X' if sys.platform == 'win32' else '✗'
    print(f"{Colors.RED}{symbol} {text}{Colors.END}")

def print_info(text: str):
    """Print info message"""
    symbol = 'i' if sys.platform == 'win32' else 'ℹ'
    print(f"{Colors.YELLOW}{symbol} {text}{Colors.END}")

def check_dependencies() -> bool:
    """Verify required binaries and directories exist"""
    print_info("Checking dependencies...")
    
    # # Check Python modules
    # required_modules = ['paho.mqtt', 'rasa', 'flask', 'sounddevice']
    # missing_modules = []
    
    # for module in required_modules:
    #     try:
    #         __import__(module.replace('.', '/'))
    #     except ImportError:
    #         missing_modules.append(module)
    
    # if missing_modules:
    #     print_error(f"Missing Python modules: {', '.join(missing_modules)}")
    #     print_info("Run: pip install -r requirements.txt")
    #     return False
    
    # Check directories
    required_dirs = ['AUD_CAP', 'AUD_PRO', 'AUD_RET']
    for directory in required_dirs:
        if not Path(directory).exists():
            print_error(f"Directory not found: {directory}")
            return False
    
    # Check if Rasa is trained
    if not Path('AUD_PRO/models').exists() or not list(Path('AUD_PRO/models').glob('*.tar.gz')):
        print_error("No trained Rasa model found in AUD_PRO/models/")
        print_info("Run: cd AUD_PRO && rasa train")
        return False
    
    print_success("All dependencies OK")
    return True

def ensure_log_directories():
    """Create log directories if they don't exist"""
    log_dirs = ['AUD_CAP/logs', 'AUD_PRO/logs', 'AUD_RET/logs', 'logs']
    for log_dir in log_dirs:
        Path(log_dir).mkdir(parents=True, exist_ok=True)

def is_service_running(name: str) -> bool:
    """Check if a service is already running"""
    try:
        if sys.platform == 'win32':
            # Windows: Check tasklist
            result = subprocess.run(
                ['tasklist'],
                capture_output=True,
                text=True
            )
            return name.lower() in result.stdout.lower()
        else:
            # Unix: Check pgrep
            result = subprocess.run(
                ['pgrep', '-f', name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
    except:
        return False

def start_service(
    name: str,
    command: List[str],
    cwd: Optional[str] = None,
    log_file: Optional[str] = None,
    wait_time: int = 2,
    check_pattern: Optional[str] = None
) -> bool:
    """Start a background service"""
    print(f"Starting {name}...")
    
    # Check if already running
    if check_pattern and is_service_running(check_pattern):
        print_info(f"{name} already running")
        return True
    
    try:
        # Prepare log file
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = open(log_path, 'a', encoding='utf-8')
        else:
            log_handle = subprocess.DEVNULL
        
        # Start process
        if sys.platform == 'win32':
            # Windows: Use CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=log_handle,
                stderr=log_handle,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            # Unix: Use process group
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=log_handle,
                stderr=log_handle,
                preexec_fn=os.setsid
            )
        
        # Register process
        processes.append((name, process))
        
        # Wait for startup
        time.sleep(wait_time)
        
        # Check if still running
        if process.poll() is None:
            print_success(f"{name} started (PID: {process.pid})")
            return True
        else:
            print_error(f"{name} failed to start (check logs: {log_file})")
            return False
    
    except Exception as e:
        print_error(f"{name} error: {e}")
        return False

def stop_all(force: bool = False):
    """Stop all services gracefully"""
    print_header("STOPPING BLUEBERRY")
    
    # Kill spawned processes
    for name, process in reversed(processes):
        try:
            print(f"Stopping {name}...")
            
            if sys.platform == 'win32':
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(process.pid)],
                    capture_output=True
                )
            else:
                if force:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    for _ in range(50):
                        if process.poll() is not None:
                            break
                        time.sleep(0.1)
                    else:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            
            print_success(f"{name} stopped")
        except Exception as e:
            print_info(f"{name} already stopped")
    
    # Cleanup: kill by name pattern
    patterns = [
        'AUD_CAP/main.py',
        'AUD_RET/output.py',
        'rasa run',
        'rasa_bridge.py',
        'time_parser.py',
        'time_daemon.py',
        'mosquitto'
    ]
    
    for pattern in patterns:
        try:
            if sys.platform != 'win32':
                subprocess.run(['pkill', '-f', pattern], capture_output=True)
        except:
            pass
    
    processes.clear()
    print_success("All services stopped")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n")
    print_info("Interrupt received, shutting down...")
    stop_all(force=False)
    sys.exit(0)

def check_status():
    """Check and display status of all services"""
    print_header("SERVICE STATUS")
    
    services = {
        'MQTT': [
            ('Mosquitto Broker', 'mosquitto'),
        ],
        'AUD_PRO (Processing)': [
            ('Rasa Server', 'rasa run'),
            ('Rasa Actions', 'rasa run actions'),
            ('Rasa Bridge', 'rasa_bridge.py'),
            ('Time Parser', 'time_parser.py'),
            ('Time Daemon', 'time_daemon.py'),
        ],
        'AUD_CAP (Capture)': [
            ('Audio Capture', 'AUD_CAP/main.py'),
        ],
        'AUD_RET (Output)': [
            ('Audio Output', 'AUD_RET/output.py'),
        ]
    }
    
    for category, service_list in services.items():
        print(f"\n{Colors.BOLD}{category}:{Colors.END}")
        for name, pattern in service_list:
            if is_service_running(pattern):
                print_success(f"{name}: Running")
            else:
                print_error(f"{name}: Stopped")

def start_mqtt_broker() -> bool:
    """Start MQTT broker (Mosquitto)"""
    print_header("STARTING MQTT BROKER")
    
    # Check if already running
    if is_service_running('mosquitto'):
        print_info("Mosquitto already running")
        return True
    
    # Check if mosquitto is installed
    try:
        result = subprocess.run(['mosquitto', '-h'], capture_output=True)
        if result.returncode not in [0, 1, 3]:  # mosquitto -h returns 3
            raise Exception("mosquitto not found")
    except:
        print_error("Mosquitto not installed")
        print_info("Install from: https://mosquitto.org/download/")
        return False
    
    # Start Mosquitto
    if sys.platform == 'win32':
        # Windows: Check if config exists
        config_file = 'mosquitto.conf' if Path('mosquitto.conf').exists() else None
        cmd = ['mosquitto', '-v'] if not config_file else ['mosquitto', '-c', config_file, '-v']
    else:
        # Linux: Use config if exists
        config_file = 'mosquitto.conf' if Path('mosquitto.conf').exists() else None
        cmd = ['mosquitto'] if not config_file else ['mosquitto', '-c', config_file]
    
    success = start_service(
        "Mosquitto MQTT Broker",
        cmd,
        None,
        'logs/mosquitto.log',
        2,
        'mosquitto'
    )
    
    if success:
        print_success("MQTT broker started on localhost:1883")
    
    return success

def start_aud_pro() -> bool:
    """Start AUD_PRO services"""
    print_header("STARTING AUD_PRO (PROCESSING)")
    
    services = [
        ("Rasa Server", ['rasa', 'run', '--enable-api', '--port', '5005'], 
         'AUD_PRO', 'AUD_PRO/logs/rasa_server.log', 4, 'rasa run'),
        
        ("Rasa Actions", ['rasa', 'run', 'actions', '--port', '5055'], 
         'AUD_PRO', 'AUD_PRO/logs/rasa_actions.log', 3, 'rasa run actions'),
        
        ("Rasa Bridge", ['py', 'rasa_bridge.py'], 
         'AUD_PRO', 'AUD_PRO/logs/rasa_bridge.log', 2, 'rasa_bridge.py'),
        
        ("Time Parser", ['py', 'time_parser.py'], 
         'AUD_PRO/services', 'AUD_PRO/logs/time_parser.log', 2, 'time_parser.py'),
        
        ("Time Daemon", ['py', 'time_daemon.py'], 
         'AUD_PRO', 'AUD_PRO/logs/time_daemon.log', 1, 'time_daemon.py'),
    ]
    
    failed = []
    for name, cmd, cwd, log, wait, check in services:
        if not start_service(name, cmd, cwd, log, wait, check):
            failed.append(name)
    
    if failed:
        print_error(f"Failed to start: {', '.join(failed)}")
        return False
    
    print_success("AUD_PRO started successfully")
    return True

def start_aud_cap() -> bool:
    """Start AUD_CAP service"""
    print_header("STARTING AUD_CAP (AUDIO CAPTURE)")
    
    success = start_service(
        "Audio Capture",
        ['py', 'main.py'],
        'AUD_CAP',
        'AUD_CAP/logs/audio_capture.log',
        2,
        'AUD_CAP/main.py'
    )
    
    if success:
        print_success("AUD_CAP started (listening for 'Blueberry')")
    
    return success

def start_aud_ret() -> bool:
    """Start AUD_RET service"""
    print_header("STARTING AUD_RET (AUDIO OUTPUT)")
    
    success = start_service(
        "Audio Output",
        ['py', 'output.py'],
        'AUD_RET',
        'AUD_RET/logs/audio_output.log',
        1,
        'AUD_RET/output.py'
    )
    
    if success:
        print_success("AUD_RET started")
    
    return success

def start_all() -> bool:
    """Start all Blueberry services"""
    print_header("BLUEBERRY VOICE ASSISTANT")
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Ensure log directories exist
    ensure_log_directories()
    
    # Start MQTT broker first
    if not start_mqtt_broker():
        print_error("Failed to start MQTT broker")
        print_info("Services require MQTT broker to communicate")
        stop_all()
        return False
    
    # Start services in order
    if not start_aud_pro():
        print_error("Failed to start AUD_PRO")
        stop_all()
        return False
    
    if not start_aud_cap():
        print_error("Failed to start AUD_CAP")
        stop_all()
        return False
    
    if not start_aud_ret():
        print_error("Failed to start AUD_RET")
        stop_all()
        return False
    
    print_header("ALL SERVICES STARTED SUCCESSFULLY")
    print_info("Say 'Blueberry' to activate")
    print_info("Press Ctrl+C to stop\n")
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description='Blueberry Voice Assistant Launcher'
    )
    
    parser.add_argument('--stop', action='store_true', help='Stop all services')
    parser.add_argument('--force-stop', action='store_true', help='Force kill all services')
    parser.add_argument('--status', action='store_true', help='Check service status')
    parser.add_argument('--logs', choices=['cap', 'pro', 'ret', 'mqtt'], help='View logs')
    
    args = parser.parse_args()
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.stop or args.force_stop:
            stop_all(force=args.force_stop)
        
        elif args.status:
            check_status()
        
        elif args.logs:
            log_files = {
                'cap': 'AUD_CAP/logs/audio_capture.log',
                'pro': 'AUD_PRO/logs/rasa_server.log',
                'ret': 'AUD_RET/logs/audio_output.log',
                'mqtt': 'logs/mosquitto.log'
            }
            log_file = log_files[args.logs]
            
            if not Path(log_file).exists():
                print_error(f"Log file not found: {log_file}")
                sys.exit(1)
            
            print_info(f"Tailing {log_file} (Ctrl+C to exit)")
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    f.seek(0, 2)
                    while True:
                        line = f.readline()
                        if line:
                            print(line, end='')
                        else:
                            time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n")
        
        else:
            # Default: start all services
            if not start_all():
                sys.exit(1)
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(1)
                    
                    # Check if any process died
                    for name, process in processes:
                        if process.poll() is not None:
                            print_error(f"{name} died unexpectedly!")
                            print_info("Check logs for details")
                            stop_all()
                            sys.exit(1)
            
            except KeyboardInterrupt:
                pass
    
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        stop_all(force=True)
        sys.exit(1)
    
    finally:
        if not (args.stop or args.force_stop or args.status or args.logs):
            stop_all()

if __name__ == "__main__":
    main()