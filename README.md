<div align="center">

# 🫐 Blueberry

### A Fully Offline Hindi Voice Assistant

*Privacy-first • Context-aware • IoT-enabled*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Rasa 3.6+](https://img.shields.io/badge/rasa-3.6+-purple.svg)](https://rasa.com/)
[![Platform: Raspberry Pi](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)](https://www.raspberrypi.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Usage](#-usage) • [Documentation](#-documentation)

---

**Blueberry** is a fully offline Hindi voice assistant achieving **2.7-second average response time** on Raspberry Pi. Complete privacy through on-device processing, custom wake word detection, and context-aware dialogue.

</div>

---

## 📖 Overview

Blueberry demonstrates that sophisticated voice interaction in Hindi is possible on edge devices without sacrificing privacy or performance. The system processes everything locally—from wake word detection to speech synthesis—eliminating cloud dependencies while maintaining natural conversation flow.

### Why Blueberry?

- **🔒 Privacy-First**: All processing happens on-device. Zero data leaves your network.
- **🇮🇳 Hindi-Optimized**: Custom temporal parser achieving 94% accuracy on Hindi expressions.
- **🧠 Context-Aware**: Remembers recent commands, enabling multi-turn conversations.
- **🏠 Smart Home Ready**: MQTT integration for Philips Hue, Tasmota, Zigbee2MQTT devices.
- **⚡ Performance**: 2.7s average response through ARM optimization (KleidiAI acceleration).
- **📦 Self-Contained**: Runs entirely offline on Raspberry Pi 4/5.

### Key Stats

| Metric | Value |
|--------|-------|
| **Response Time** | 2.7s average (2.5-3.0s range) |
| **Wake Word** | Custom "Blueberry" (Porcupine) |
| **ASR Accuracy** | 15.3% WER (VOSK Hindi medium) |
| **NLU Accuracy** | 96.2% intent, 92.8% entity F1 |
| **Temporal Parsing** | 94% (vs Duckling's 34%) |
| **Supported Intents** | 15+ across 4 domains |
| **Memory Usage** | ~1.2GB peak |

---

## ✨ Features

### Core Capabilities

🎤 **Custom Wake Word** - Responds to "Blueberry" with low false-positive rate  
🗣️ **Hindi Speech Recognition** - VOSK model optimized for CPU inference  
🧠 **Context Tracking** - Dual memory (persistent SQLite + volatile in-memory)  
⏰ **Smart Scheduling** - Alarms, timers, reminders with background daemon  
💡 **Device Control** - Lights, fans, AC via MQTT  
📝 **List Management** - Shopping lists, todo lists with persistence  
🌐 **IoT Integration** - Compatible with Philips Hue, Tasmota, Zigbee2MQTT  

### Supported Commands

<table>
<tr>
<td width="50%">

**Device Control**
- किचन की लाइट चालू करो
- बेडरूम का पंखा धीमा करो
- एसी का टेम्परेचर 22 डिग्री
- सब लाइट बंद करो

</td>
<td width="50%">

**Scheduling**
- कल सुबह 7 बजे अलार्म लगा दो
- 10 मिनट का टाइमर
- शाम को दवाई याद दिलाना
- अगले मंडे 9 बजे मीटिंग

</td>
</tr>
<tr>
<td>

**Lists**
- शॉपिंग लिस्ट में दूध ऐड करो
- टूडू लिस्ट क्या है
- होमवर्क कंप्लीट हो गया

</td>
<td>

**Information**
- क्या समय हुआ है
- आज की तारीख
- किचन की लाइट ऑन है क्या

</td>
</tr>
</table>

### Context Awareness Example

```
User: "किचन की लाइट चालू करो"
Bot:  "किचन की लाइट चालू कर दी"
      [Stores: device=light, room=kitchen]

User: "बेडरूम में भी"
Bot:  "बेडरूम की लाइट चालू कर दी"
      [Inferred: device=light from context]

User: "दोनों बंद कर दो"
Bot:  "किचन और बेडरूम की लाइट बंद कर दी"
      [Resolved: both rooms from conversation history]
```

---

## 🚀 Quick Start

### Prerequisites

**Hardware Requirements:**
- Raspberry Pi 4/5 (4GB+ RAM recommended)
- USB Microphone (16kHz sampling rate)
- Speaker (3.5mm or USB)
- MicroSD card (32GB+)

**Software Requirements:**
- Raspberry Pi OS (64-bit) or Ubuntu 24.04 ARM64
- Python 3.9+
- ~2GB free disk space

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/blueberry.git
cd blueberry

# 2. Install dependencies
pip install -r requirements.txt

# 3. Train Rasa NLU model (one-time, ~5-10 minutes)
cd AUD_PRO
rasa train
cd ..

# 4. Create log directories
mkdir -p AUD_CAP/logs AUD_PRO/logs AUD_RET/logs
```

### Quick Start

**Option 1: Makefile (Recommended for Linux/Mac)**

```bash
make start        # Start all services
make status       # Check what's running
make logs-cap     # View audio capture logs
make stop         # Stop everything
```

**Option 2: Python Launcher (Cross-platform)**

```bash
python launcher.py              # Start all services
python launcher.py --status     # Check status
python launcher.py --logs cap   # View logs
python launcher.py --stop       # Stop all
```

**That's it!** Say **"Blueberry"** to activate, then speak your command in Hindi.

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    BLUEBERRY PIPELINE                        │
└─────────────────────────────────────────────────────────────┘

   AUD_CAP              AUD_PRO                AUD_RET
 ┌──────────┐        ┌────────────┐         ┌──────────┐
 │ Wake Word│  MQTT  │    NLU     │  MQTT   │   TTS    │
 │   + VAD  │───────▶│  Actions   │────────▶│ Playback │
 │  + Audio │        │  Temporal  │         │          │
 └──────────┘        └────────────┘         └──────────┘
      ↓                    ↓                      ↓
  Porcupine         Rasa + VOSK             eSpeak-ng
  sounddevice       KleidiAI              
  webrtcvad         Custom Parser
```

### Component Details

| Module | Services | Responsibility |
|--------|----------|----------------|
| **AUD_CAP** | `main.py` | • Porcupine wake word detection<br>• webrtcvad speech endpoint<br>• Audio buffering & MQTT publish |
| **AUD_PRO** | `rasa run`<br>`rasa run actions`<br>`rasa_bridge.py`<br>`time_parser.py`<br>`time_daemon.py` | • VOSK ASR transcription<br>• DIET intent/entity extraction (KleidiAI)<br>• Custom Hindi temporal parsing<br>• Business logic execution<br>• Alarm/timer background daemon |
| **AUD_RET** | `output.py` | • eSpeak-ng speech synthesis<br>• Audio playback via speakers |

### Data Flow

1. **Wake Word** → Porcupine detects "Blueberry" → Start audio buffering
2. **VAD** → webrtcvad detects speech end → Trigger ASR
3. **ASR** → VOSK transcribes Hindi audio → Text output
4. **NLU** → Rasa DIET classifies intent/entities → Structured data
5. **Temporal** → Custom parser extracts time expressions → ISO 8601
6. **Action** → Execute business logic → Generate response text
7. **TTS** → eSpeak synthesizes Hindi speech → Audio output
8. **Playback** → Speaker plays response

**Average Latency Breakdown:**
- Wake word: 100ms
- Audio capture: 500ms
- VOSK ASR: 320ms
- Rasa NLU: 1800ms (KleidiAI optimized)
- Temporal parse: 30ms
- Action execution: 80ms
- TTS synthesis: 70ms
- **Total: ~2.7 seconds**

---

## 📚 Technology Stack

<table>
<tr>
<td><b>Layer</b></td>
<td><b>Technology</b></td>
<td><b>Why This Choice</b></td>
</tr>
<tr>
<td>Wake Word</td>
<td>Porcupine</td>
<td>Offline, custom wake word, low false-positive rate</td>
</tr>
<tr>
<td>VAD</td>
<td>webrtcvad</td>
<td>Reliable speech endpoint detection, low latency</td>
</tr>
<tr>
<td>ASR</td>
<td>VOSK (Hindi medium)</td>
<td>Best CPU performance (15.3% WER, 320ms latency)</td>
</tr>
<tr>
<td>NLU</td>
<td>Rasa DIET</td>
<td>Joint intent/entity extraction, context support</td>
</tr>
<tr>
<td>Acceleration</td>
<td>ARM KleidiAI</td>
<td>TensorFlow optimization for ARM (4.2s → 1.8s)</td>
</tr>
<tr>
<td>Temporal Parse</td>
<td>Custom Python</td>
<td>Hindi-specific patterns (94% vs Duckling 34%)</td>
</tr>
<tr>
<td>Database</td>
<td>SQLite</td>
<td>Zero-config persistence, WAL mode for concurrency</td>
</tr>
<tr>
<td>IoT Bus</td>
<td>MQTT (Mosquitto)</td>
<td>Lightweight pub-sub, standard for smart home</td>
</tr>
<tr>
<td>TTS</td>
<td>eSpeak-ng</td>
<td>Minimal latency (70ms), small footprint</td>
</tr>
</table>

---

## 💡 Usage Examples

### Basic Commands

```bash
# Start the assistant
make start

# Say the wake word
"Blueberry"

# Device control
"किचन की लाइट चालू करो"
"बेडरूम का पंखा बंद करो"
"लिविंग रूम की लाइट 50 परसेंट"

# Scheduling
"कल सुबह 7 बजे अलार्म लगा दो"
"10 मिनट का टाइमर"
"शाम 6 बजे दवाई याद दिलाना"

# Lists
"शॉपिंग लिस्ट में दूध ऐड करो"
"टूडू लिस्ट क्या है"

# Information
"क्या समय हुआ है"
"किचन की लाइट ऑन है क्या"
```

### Advanced: IoT Integration

**Compatible Devices:**
- Philips Hue (via MQTT bridge)
- Tasmota-flashed devices (ESP8266/ESP32)
- Zigbee2MQTT devices (Xiaomi, IKEA, etc.)
- Home Assistant integration
- Custom ESP32/Arduino MQTT clients

**MQTT Topic Structure:**
```
home/bedroom/light/command    → ON/OFF
home/bedroom/light/brightness → 0-100
home/bedroom/fan/command      → ON/OFF
home/bedroom/fan/speed        → 1-4
```

**Example: Voice command → MQTT → Device**
```
User: "सब लाइट बंद करो"
  ↓
Action server publishes:
  home/living_room/light/command OFF
  home/bedroom/light/command OFF
  home/kitchen/light/command OFF
  ↓
Devices respond within 200ms
```

---

## 🛠️ Development

### Rough Project Structure- The Main Important Files 

```
blueberry/
├── AUD_CAP/              # Audio capture module
│   ├── main.py           # Wake word + VAD + MQTT publisher
│   └── logs/
├── AUD_PRO/              # Processing module
│   ├── actions/          # Rasa action server
│   ├── data/             # Training data (NLU, stories, rules)
│   ├── models/           # Trained Rasa models
│   ├── services/
│   │   ├── time_parser.py    # Custom Hindi temporal parser
│   │   └── time_daemon.py    # Background alarm/timer daemon
│   ├── rasa_bridge.py    # MQTT ↔ Rasa integration
│   ├── config.yml        # Rasa NLU pipeline
│   ├── domain.yml        # Intents, entities, responses
│   └── logs/
├── AUD_RET/              # Audio output module
│   ├── output.py         # TTS + playback
│   └── logs/
├── database/
│   ├── schema.sql        # SQLite database schema
│   └── blueberry.db      # Persistent storage
├── Makefile              # Service management (Linux/Mac)
├── launcher.py           # Cross-platform launcher
├── requirements.txt      # Python dependencies
└── README.md
```

### Adding New Intents

1. **Define intent in `AUD_PRO/data/nlu.yml`:**

```yaml
- intent: play_music
  examples: |
    - गाना चलाओ
    - music play करो
    - [देशी](genre) गाने सुनना है
```

2. **Add action in `AUD_PRO/actions/actions.py`:**

```python
class ActionPlayMusic(Action):
    def name(self):
        return "action_play_music"
    
    def run(self, dispatcher, tracker, domain):
        genre = tracker.get_slot("genre")
        # Your music playback logic
        dispatcher.utter_message(text=f"{genre} गाना चला रहा हूं")
        return []
```

3. **Update `AUD_PRO/domain.yml`:**

```yaml
intents:
  - play_music

actions:
  - action_play_music
```

4. **Retrain:**

```bash
cd AUD_PRO && rasa train
```

### Performance Tuning

**If experiencing high latency:**

```bash
# Check which service is slow
make status
python launcher.py --status

# View logs
make logs-pro
python launcher.py --logs pro

# Common fixes:
# 1. Ensure KleidiAI is installed
pip install tensorflow-aarch64-kleidiAI

# 2. Check VOSK model size
ls -lh AUD_PRO/models/vosk-model-hi-*

# 3. Verify localhost resolution
ping 127.0.0.1  # Should be <1ms
```

---

## 📊 Performance Benchmarks

### Latency Comparison

| System | Platform | Language | Response Time |
|--------|----------|----------|---------------|
| Amazon Alexa | Cloud | Hindi | 800-1500ms |
| Google Assistant | Cloud | Hindi | 900-1200ms |
| Mycroft AI | RPi 4 | English | 3000-5000ms |
| Rhasspy | RPi 4 | English | 2000-4000ms |
| **Blueberry** | **RPi 4** | **Hindi** | **2500-3000ms** |

### Accuracy Metrics

| Component | Metric | Score |
|-----------|--------|-------|
| Wake Word | False Positive Rate | <1 per 48 hours |
| ASR (VOSK) | Word Error Rate | 15.3% |
| NLU (Rasa) | Intent Accuracy | 96.2% |
| NLU (Rasa) | Entity F1 Score | 92.8% |
| Temporal Parser | Overall Accuracy | 94% |

---

## 🐛 Troubleshooting

### Common Issues

**Issue: Wake word not detected**
```bash
# Check microphone
arecord -l

# Test audio input
cd AUD_CAP && python -c "import sounddevice; print(sounddevice.query_devices())"

# Verify Porcupine model
ls ~/.local/share/porcupine/  # Should contain blueberry_*.ppn
```

**Issue: Rasa fails to start**
```bash
# Verify model trained
ls AUD_PRO/models/*.tar.gz

# Retrain if missing
cd AUD_PRO && rasa train

# Check Rasa version
rasa --version  # Should be 3.6+
```

**Issue: High latency (>5 seconds)**
```bash
# Check KleidiAI installation
python -c "import tensorflow as tf; print(tf.__version__)"

# Verify localhost resolution (should be <1ms)
ping 127.0.0.1

# Check CPU usage
htop  # Rasa should use ~60-80% during inference
```

**Issue: No TTS output**
```bash
# Test speaker
speaker-test -t wav -c 2

# Verify eSpeak installation
espeak-ng --version

# Check AUD_RET logs
tail -f AUD_RET/logs/audio_output.log
```

### Getting Help

- **Logs**: Check `AUD_*/logs/*.log` for detailed error messages
- **Status**: Run `make status` to see which services are running
- **Issues**: Open an issue on GitHub with logs attached
- **Discussions**: Join GitHub Discussions for questions

---

## 📖 Documentation

### Additional Resources

- **[Installation Guide](docs/INSTALL.md)** - Detailed setup instructions
- **[Architecture Deep Dive](docs/ARCHITECTURE.md)** - System design details
- **[API Reference](docs/API.md)** - MQTT topics, action server endpoints
- **[Contributing Guide](CONTRIBUTING.md)** - Development workflow
- **[Changelog](CHANGELOG.md)** - Version history

### Research Paper

This project is documented in an academic report available in this repository:
- **[Project Report](docs/Blueberry_Voice_Assistant_Report.docx)** - Comprehensive technical documentation including methodology, challenges, and performance analysis

---

## 🤝 Contributing

Contributions are welcome! Whether it's bug fixes, new features, documentation improvements, or additional language support.

### Development Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/blueberry.git
cd blueberry

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/
```

### Contribution Areas

- 🌐 **Language Support**: Add support for other Indian languages
- 🎯 **Intent Expansion**: Contribute new intents and training data
- 🏠 **IoT Integrations**: Add support for more smart home platforms
- 🧪 **Testing**: Improve test coverage and CI/CD
- 📚 **Documentation**: Tutorials, examples, translations

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **VOSK** for excellent offline ASR
- **Rasa** for the NLU framework
- **ARM** for KleidiAI optimization library
- **Picovoice** for Porcupine wake word engine
- **Open-source community** for foundational tools

---

## 📞 Contact

**Author**: [Vedant Singh]  
**Email**: vedant.240102162@iiitbh.ac.in 

---

<div align="center">

Made with ❤️ for the Hindi-speaking community

**⭐ Star this repo if you find it useful!**

</div>
