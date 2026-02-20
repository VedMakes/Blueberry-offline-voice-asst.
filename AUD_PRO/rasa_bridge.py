"""
Rasa MQTT Bridge
Connects MQTT to Rasa HTTP API
"""

import json
import logging
import paho.mqtt.client as mqtt
import requests
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RasaBridge:
    """Bridge between MQTT and Rasa HTTP API"""
    
    def __init__(self, 
                 mqtt_broker="localhost", 
                 mqtt_port=1883,
                 rasa_url="http://localhost:5005"):
        
        self.rasa_url = rasa_url
        self.rasa_parse_endpoint = f"{rasa_url}/model/parse"
        
        # MQTT setup
        self.mqtt_client = mqtt.Client(client_id="rasa_bridge")
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        
        try:
            self.mqtt_client.connect(mqtt_broker, mqtt_port, 60)
            logger.info(f"Connecting to MQTT: {mqtt_broker}:{mqtt_port}")
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            raise
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("✓ MQTT connected")
            
            # Subscribe to ASR output
            client.subscribe("asr/text")
            logger.info("Subscribed to: asr/text")
            
            # Publish ready status
            client.publish("system/status", json.dumps({
                "service": "rasa_bridge",
                "status": "ready",
                "timestamp": datetime.now().isoformat()
            }))
        else:
            logger.error(f"✗ MQTT connection failed with code {rc}")
    
    def on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            if msg.topic == "asr/text":
                data = json.loads(msg.payload)
                self.handle_asr_text(data)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_asr_text(self, data):
        """Process transcribed text from ASR"""
        text = data.get('text', '')
        confidence = data.get('confidence', 100)
        
        logger.info(f"\n{'='*50}")
        logger.info(f"📝 Received: {text} (confidence: {confidence}%)")
        
        if confidence < 70:
            logger.warning("❌ Low confidence, rejecting")
            self.publish_response("माफ करें, समझ नहीं आया", intent="low_confidence")
            return
        
        if not text.strip():
            logger.warning("❌ Empty text, ignoring")
            return
        
        # Call Rasa NLU
        try:
            logger.info("→ Calling Rasa...")
            response = requests.post(
                self.rasa_parse_endpoint,
                json={"text": text},
                timeout=5
            )
            response.raise_for_status()
            intent_data = response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Rasa API error: {e}")
            self.publish_response("कुछ गड़बड़ हो गई", intent="rasa_error")
            return
        
        # Extract intent info
        intent_name = intent_data.get('intent', {}).get('name', 'unknown')
        intent_confidence = intent_data.get('intent', {}).get('confidence', 0)
        entities = intent_data.get('entities', [])
        
        logger.info(f"🎯 Intent: {intent_name} ({intent_confidence:.2f})")
        logger.info(f"📦 Entities: {entities}")
        
        if intent_confidence < 0.5:
            logger.warning("❌ Low intent confidence")
            self.publish_response("मुझे यह समझ नहीं आया", intent="low_intent_confidence")
            return
        
        # Call Rasa Dialogue (to trigger actions)
        try:
            logger.info("→ Triggering Rasa dialogue...")
            
            dialogue_endpoint = f"{self.rasa_url}/webhooks/rest/webhook"
            dialogue_response = requests.post(
                dialogue_endpoint,
                json={
                    "sender": "user",
                    "message": text
                },
                timeout=10
            )
            dialogue_response.raise_for_status()
            bot_responses = dialogue_response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Rasa dialogue error: {e}")
            self.publish_response("कुछ गड़बड़ हो गई", intent="dialogue_error")
            return
        
        # Extract bot responses
        if bot_responses:
            for bot_msg in bot_responses:
                response_text = bot_msg.get('text', '')
                if response_text:
                    logger.info(f"💬 Response: {response_text}")
                    self.publish_response(response_text, intent=intent_name)
        else:
            logger.warning("⚠️  No response from Rasa")
            # Fallback response
            self.publish_response("ठीक है", intent=intent_name)
        
        logger.info(f"{'='*50}\n")
    
    def publish_response(self, text: str, intent: str = None):
        """Publish response to MQTT for TTS"""
        message = {
            "text": text,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        }
        
        # Publish to TTS topic
        self.mqtt_client.publish("tts/speak", json.dumps(message))
        logger.info(f"✓ Published to tts/speak: {text}")
    
    def run(self):
        """Start the bridge"""
        logger.info("🌉 Rasa Bridge starting...")
        logger.info(f"Rasa URL: {self.rasa_url}")
        logger.info("Waiting for messages...\n")
        
        try:
            # Blocking call
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            logger.info("\n👋 Shutting down Rasa Bridge...")
            self.mqtt_client.disconnect()


if __name__ == "__main__":
    bridge = RasaBridge()
    bridge.run()

