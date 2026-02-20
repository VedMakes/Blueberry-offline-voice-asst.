import json
import time
import paho.mqtt.client as mqtt
from SECRETS import MQTT_BROKER, MQTT_PORT

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client(client_id="audio_client")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self._connected = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print(" MQTT connected")
            self._connected = True
            
            # Subscribe to topics we care about
            client.subscribe("system/status")
            client.subscribe("tts/status")
            
            # Publish ready status
            client.publish("system/status", json.dumps({
                "client": "audio",
                "status": "ready",
                "timestamp": time.time()
            }))
        else:
            print(f" MQTT connection failed with code {rc}")
            self._connected = False
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received"""
        try:
            data = json.loads(msg.payload)
            print(f"[MQTT ←] {msg.topic}: {data}")
        except json.JSONDecodeError:
            print(f"[MQTT ←] {msg.topic}: {msg.payload}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected"""
        print(f"[MQTT] Disconnected with code {rc}")
        self._connected = False
    
    def connect(self):
        """Connect to MQTT broker (blocking until connected)"""
        print("Attempting MQTT connect...")
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()  # Start background thread
            
            # Wait for connection (with timeout)
            timeout = 10
            start = time.time()
            while not self._connected and (time.time() - start) < timeout:
                time.sleep(0.1)
            
            if not self._connected:
                raise Exception("MQTT connection timeout")
            
            print("MQTT connected successfully")
            
        except Exception as e:
            print(f"MQTT connect failed: {e}")
            raise
    
    def send_text(self, text):
        """Publish transcribed text to MQTT"""
        if not self._connected:
            print("MQTT not connected, skipping send")
            return False
        
        try:
            print(f"→ Publishing: {text}")
            
            message = json.dumps({
                "text": text,
                "timestamp": time.time()
            })
            
            result = self.client.publish("asr/text", message, qos=0)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(" Published successfully")
                return True
            else:
                print(f" Publish failed with code {result.rc}")
                return False
            
        except Exception as e:
            print(f" Publish error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self._connected = False
        self.client.loop_stop()
        self.client.disconnect()
        print("[MQTT] Disconnected")