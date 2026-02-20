from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from datetime import datetime, timedelta
import logging
import json
import paho.mqtt.client as mqtt
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database.db_manager import get_db
except ImportError:
    sys.path.append('..')
    from database.db_manager import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== DUCKLING HELPER ====================

def extract_duckling_value(entity):
    """
    Extract value from Duckling entity
    
    For time: returns ISO 8601 string
    For duration: returns seconds (int)
    """
    if not entity:
        return None
    
    # If it's already a string/int, return as-is
    if isinstance(entity, (str, int, float)):
        return entity
    
    # If it's a dict (Duckling format)
    if isinstance(entity, dict):
        # Check if it has 'value' key (Duckling format)
        if 'value' in entity:
            value_obj = entity['value']
            
            # For time dimensions
            if 'value' in value_obj and isinstance(value_obj['value'], str):
                return value_obj['value']  # ISO string
            
            # For duration dimensions
            elif 'value' in value_obj and 'unit' in value_obj:
                # Return seconds
                return int(value_obj['value'])
        
        # Maybe it's just the value object itself
        elif 'value' in entity and isinstance(entity['value'], str):
            return entity['value']
    
    # Fallback
    return None

def format_time_hindi(iso_string: str) -> str:
    """Format ISO datetime to Hindi-friendly string"""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        
        # Format: "17 फरवरी शाम 5 बजे"
        hour = dt.hour
        if hour == 0:
            time_str = "मध्यरात्रि 12 बजे"
        elif hour < 12:
            time_str = f"सुबह {hour} बजे"
        elif hour == 12:
            time_str = "दोपहर 12 बजे"
        elif hour < 17:
            time_str = f"दोपहर {hour - 12} बजे"
        elif hour < 21:
            time_str = f"शाम {hour - 12} बजे"
        else:
            time_str = f"रात {hour - 12} बजे"
        
        return time_str
    except:
        return iso_string

def format_duration_hindi(seconds: int) -> str:
    """Format seconds to Hindi-friendly string"""
    if seconds < 60:
        return f"{seconds} सेकंड"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} मिनट"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours} घंटे {minutes} मिनट"
        return f"{hours} घंटे"

# ==================== MQTT CLIENT SINGLETON ====================

class MQTTPublisher:
    """Singleton MQTT client for publishing commands"""
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not MQTTPublisher._initialized:
            self.client = mqtt.Client(client_id="rasa_actions")
            self.connected = False
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            try:
                broker = os.getenv("MQTT_BROKER", "localhost")
                port = int(os.getenv("MQTT_PORT", 1883))
                
                self.client.connect(broker, port, 60)
                self.client.loop_start()
                logger.info(f"MQTT connecting to {broker}:{port}")
            except Exception as e:
                logger.error(f"MQTT connection failed: {e}")
            
            MQTTPublisher._initialized = True
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info("✓ MQTT connected")
            self.publish("system/status", {
                "service": "rasa_actions",
                "status": "ready",
                "timestamp": datetime.now().isoformat()
            })
        else:
            self.connected = False
            logger.error(f"✗ MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        logger.warning(f"MQTT disconnected with code {rc}")
    
    def publish(self, topic: str, payload: dict):
        if not self.connected:
            logger.warning(f"MQTT not connected, cannot publish to {topic}")
            return False
        
        try:
            payload_json = json.dumps(payload)
            result = self.client.publish(topic, payload_json, qos=0)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"→ Published to {topic}")
                return True
            else:
                logger.error(f"✗ Publish failed to {topic}, code: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"✗ Publish error to {topic}: {e}")
            return False

mqtt_pub = MQTTPublisher()

# ==================== BASE ACTION CLASS ====================

class BaseDeviceAction(Action):
    """Base class for device actions"""
    def name(self) -> Text:
        return "action_base_device"
    
    def get_room_device(self, tracker: Tracker) -> tuple:
        room = tracker.get_slot("room")
        device = tracker.get_slot("device")
        
        if not room or not device:
            context_device = tracker.get_slot("context_device")
            if context_device and "_" in context_device:
                parts = context_device.split("_", 1)
                room = room or parts[0]
                device = device or parts[1]
        
        room = room or "लिविंग रूम"
        device = device or "लाइट"
        
        return room, device

# ==================== DEVICE CONTROL ACTIONS ====================

class ActionTurnOnDevice(BaseDeviceAction):
    def name(self) -> Text:
        return "action_turn_on_device"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        room, device = self.get_room_device(tracker)
        
        try:
            mqtt_pub.publish(f"device/{room}/{device}/command", {
                "action": "on",
                "room": room,
                "device": device,
                "timestamp": datetime.now().isoformat()
            })

            device_responses = {
                "लाइट": f"{room} की लाइट चालू कर दी",
                "पंखा": f"{room} का पंखा चालू कर दिया",
                "एसी": f"{room} का एसी चालू कर दिया",
            }
            
            response = device_responses.get(device, f"{room} की {device} चालू कर दी")
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Turn on: {room} - {device}")
            
            return [
                SlotSet("room", room),
                SlotSet("device", device),
                SlotSet("context_device", f"{room}_{device}")
            ]
        except Exception as e:
            logger.error(f"✗ Turn on device failed: {e}")
            dispatcher.utter_message(text="कुछ गड़बड़ हो गई")
            return []


class ActionTurnOffDevice(BaseDeviceAction):
    def name(self) -> Text:
        return "action_turn_off_device"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        room, device = self.get_room_device(tracker)
        
        try:
            mqtt_pub.publish(f"device/{room}/{device}/command", {
                "action": "off",
                "room": room,
                "device": device,
                "timestamp": datetime.now().isoformat()
            })

            device_responses = {
                "लाइट": f"{room} की लाइट बंद कर दी",
                "पंखा": f"{room} का पंखा बंद कर दिया",
                "एसी": f"{room} का एसी बंद कर दिया",
            }
            
            response = device_responses.get(device, f"{room} की {device} बंद कर दी")
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Turn off: {room} - {device}")
            
            return [
                SlotSet("room", room),
                SlotSet("device", device),
                SlotSet("context_device", f"{room}_{device}")
            ]
        except Exception as e:
            logger.error(f"✗ Turn off device failed: {e}")
            dispatcher.utter_message(text="कुछ गड़बड़ हो गई")
            return []


class ActionSetBrightness(BaseDeviceAction):
    def name(self) -> Text:
        return "action_set_brightness"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        room, device = self.get_room_device(tracker)
        brightness = tracker.get_slot("brightness")
        
        try:
            if brightness is None:
                brightness = 50
            else:
                brightness = int(float(brightness))
                brightness = max(0, min(100, brightness))
        except (ValueError, TypeError):
            brightness = 50
        
        try:
            mqtt_pub.publish(f"device/{room}/{device}/command", {
                "action": "brightness",
                "level": brightness,
                "room": room,
                "device": device,
                "timestamp": datetime.now().isoformat()
            })
            
            
            response = f"{room} की {device} {brightness}% पर सेट कर दी"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Brightness: {room} - {device} - {brightness}%")
            
            return [
                SlotSet("room", room),
                SlotSet("device", device),
                SlotSet("brightness", brightness)
            ]
        except Exception as e:
            logger.error(f"✗ Set brightness failed: {e}")
            dispatcher.utter_message(text="brightness सेट नहीं हो सकी")
            return []


class ActionSetFanSpeed(BaseDeviceAction):
    def name(self) -> Text:
        return "action_set_fan_speed"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        room, device = self.get_room_device(tracker)
        speed = tracker.get_slot("speed") or "मध्यम"
        
        speed_map = {
            "धीमा": 1, "slow": 1, "1": 1,
            "मध्यम": 2, "medium": 2, "2": 2,
            "तेज": 3, "fast": 3, "3": 3, "high": 3,
            "4": 4, "full": 4, "पूरा": 4
        }
        
        speed_num = speed_map.get(str(speed).lower(), 2)
        
        try:
            mqtt_pub.publish(f"device/{room}/fan/command", {
                "action": "speed",
                "level": speed_num,
                "room": room,
                "device": "fan",
                "timestamp": datetime.now().isoformat()
            })

            response = f"{room} का पंखा {speed} स्पीड पर सेट कर दिया"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Fan speed: {room} - {speed} ({speed_num})")
            
            return [
                SlotSet("room", room),
                SlotSet("device", "fan"),
                SlotSet("speed", speed)
            ]
        except Exception as e:
            logger.error(f"✗ Set fan speed failed: {e}")
            dispatcher.utter_message(text="पंखे की स्पीड सेट नहीं हो सकी")
            return []


class ActionSetTemperature(BaseDeviceAction):
    def name(self) -> Text:
        return "action_set_temperature"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        room, device = self.get_room_device(tracker)
        temperature = tracker.get_slot("temperature")
        
        try:
            if temperature is None:
                temperature = 24
            else:
                temperature = int(float(temperature))
                temperature = max(16, min(30, temperature))
        except (ValueError, TypeError):
            temperature = 24
        
        try:
            mqtt_pub.publish(f"device/{room}/ac/command", {
                "action": "temperature",
                "value": temperature,
                "room": room,
                "device": "ac",
                "timestamp": datetime.now().isoformat()
            })
            
            db = get_db()
            db.update_device_state(room, "ac", "on", temperature=temperature)
            
            response = f"{room} का एसी {temperature} डिग्री पर सेट कर दिया"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Temperature: {room} - {temperature}°C")
            
            return [
                SlotSet("room", room),
                SlotSet("device", "ac"),
                SlotSet("temperature", temperature)
            ]
        except Exception as e:
            logger.error(f"✗ Set temperature failed: {e}")
            dispatcher.utter_message(text="तापमान सेट नहीं हो सका")
            return []

class ActionSetAlarm(Action):
    def name(self) -> Text:
        return "action_set_alarm"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # FIX: Extract ISO string from Duckling entity
        alarm_time_entity = tracker.get_slot("alarm_time")
        alarm_time_iso = extract_duckling_value(alarm_time_entity)
        
        if not alarm_time_iso:
            dispatcher.utter_message(text="किस समय अलार्म लगाना है?")
            return []
        
        try:
            # Save to database with ISO string
            db = get_db()
            alarm_id = db.add_alarm(alarm_time_iso, name="alarm")
            
            # Publish to MQTT
            mqtt_pub.publish("alarm/set", {
                "id": alarm_id,
                "time": alarm_time_iso,
                "timestamp": datetime.now().isoformat()
            })
            
            # Format response
            time_str = format_time_hindi(alarm_time_iso)
            response = f"{time_str} का अलार्म सेट कर दिया"
            
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Alarm set: {alarm_time_iso} (ID: {alarm_id})")
            
            return [SlotSet("time", alarm_time_iso)]
        
        except Exception as e:
            logger.error(f"✗ Set alarm failed: {e}")
            dispatcher.utter_message(text="अलार्म सेट नहीं हो सका")
            return []


class ActionCancelAlarm(Action):
    def name(self) -> Text:
        return "action_cancel_alarm"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        alarm_time_entity = tracker.get_slot("alarm_time")
        alarm_time_iso = extract_duckling_value(alarm_time_entity)
        
        try:
            db = get_db()
            
            if alarm_time_iso:
                # FIX: Use correct parameter name
                db.cancel_alarm(alarm_datetime=alarm_time_iso)
                time_str = format_time_hindi(alarm_time_iso)
                response = f"{time_str} का अलार्म रद्द कर दिया"
            else:
                db.cancel_alarm()
                response = "सभी अलार्म रद्द कर दिए"
            
            mqtt_pub.publish("alarm/cancel", {
                "time": alarm_time_iso,
                "timestamp": datetime.now().isoformat()
            })
            
            dispatcher.utter_message(text=response)
            return []
        
        except Exception as e:
            logger.error(f"✗ Cancel alarm failed: {e}")
            dispatcher.utter_message(text="अलार्म रद्द नहीं हो सका")
            return []


class ActionListAlarms(Action):
    def name(self) -> Text:
        return "action_list_alarms"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            db = get_db()
            alarms = db.get_active_alarms()
            
            if not alarms:
                response = "कोई अलार्म सेट नहीं है"
            else:
                alarm_texts = []
                for alarm in alarms:
                    time_str = format_time_hindi(alarm['alarm_datetime'])
                    name_str = f" ({alarm['name']})" if alarm.get('name') else ""
                    alarm_texts.append(f"{time_str}{name_str}")
                
                alarm_list = ", ".join(alarm_texts)
                response = f"आपके अलार्म: {alarm_list}"
            
            dispatcher.utter_message(text=response)
            logger.info(f"✓ Listed {len(alarms)} alarms")
            return []
        
        except Exception as e:
            logger.error(f"✗ List alarms failed: {e}")
            dispatcher.utter_message(text="अलार्म देख नहीं सके")
            return []


# ==================== REMINDER ACTIONS (FIXED) ====================

class ActionSetReminder(Action):
    def name(self) -> Text:
        return "action_set_reminder"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # FIX: Extract ISO string from Duckling
        reminder_time_entity = tracker.get_slot("reminder_time")
        reminder_time_iso = extract_duckling_value(reminder_time_entity)
        
        reminder_text =  tracker.get_slot("reminder_text") or tracker.get_slot("event_name")
        
        if not reminder_time_iso:
            dispatcher.utter_message(text="कब याद दिलाना है?")
            return []
        
        if not reminder_text:
            dispatcher.utter_message(text="क्या याद दिलाना है?")
            return []
        
        try:
            db = get_db()
            reminder_id = db.add_reminder(reminder_time_iso, reminder_text)
            
            mqtt_pub.publish("reminder/set", {
                "id": reminder_id,
                "time": reminder_time_iso,
                "text": reminder_text,
                "timestamp": datetime.now().isoformat()
            })
            
            time_str = format_time_hindi(reminder_time_iso)
            response = f"ठीक है, {time_str} को '{reminder_text}' याद दिला दूंगा"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Reminder set: {reminder_time_iso} - {reminder_text}")
            
            return [
                SlotSet("time", reminder_time_iso),
                SlotSet("reminder_text", reminder_text)
            ]
        
        except Exception as e:
            logger.error(f"✗ Set reminder failed: {e}")
            dispatcher.utter_message(text="रिमाइंडर सेट नहीं हो सका")
            return []


# ==================== TIMER ACTIONS (FIXED) ====================

class ActionSetTimer(Action):
    def name(self) -> Text:
        return "action_set_timer"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # FIX: Extract seconds from Duckling duration entity
        duration_entity = tracker.get_slot("timer_duration")
        duration_seconds = extract_duckling_value(duration_entity)
        
        if not duration_seconds:
            dispatcher.utter_message(text="कितने समय का टाइमर लगाना है?")
            return []
        
        try:
            db = get_db()
            timer_id = db.add_timer(duration_seconds, name="timer")
            
            mqtt_pub.publish("timer/set", {
                "id": timer_id,
                "duration_seconds": duration_seconds,
                "timestamp": datetime.now().isoformat()
            })
            
            duration_str = format_duration_hindi(duration_seconds)
            response = f"{duration_str} का टाइमर शुरू कर दिया"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Timer set: {duration_seconds}s (ID: {timer_id})")
            
            return [SlotSet("duration", duration_seconds)]
        
        except Exception as e:
            logger.error(f"✗ Set timer failed: {e}")
            dispatcher.utter_message(text="टाइमर सेट नहीं हो सका")
            return []


class ActionCancelTimer(Action):
    def name(self) -> Text:
        return "action_cancel_timer"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            db = get_db()
            db.cancel_timer()
            
            mqtt_pub.publish("timer/cancel", {
                "timestamp": datetime.now().isoformat()
            })
            
            response = "टाइमर रद्द कर दिया"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Timer(s) cancelled")
            return []
        
        except Exception as e:
            logger.error(f"✗ Cancel timer failed: {e}")
            dispatcher.utter_message(text="टाइमर रद्द नहीं हो सका")
            return []


class ActionCheckTimer(Action):
    def name(self) -> Text:
        return "action_check_timer"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            db = get_db()
            timers = db.get_active_timers()
            
            if not timers:
                response = "कोई टाइमर चालू नहीं है"
            else:
                timer = timers[0]
                end_time = datetime.fromisoformat(timer['end_datetime'])
                remaining = (end_time - datetime.now()).total_seconds()
                remaining = max(0, remaining)
                
                duration_str = format_duration_hindi(int(remaining))
                response = f"टाइमर में {duration_str} बाकी हैं"
            
            dispatcher.utter_message(text=response)
            logger.info(f"✓ Timer check: {len(timers)} active")
            return []
        
        except Exception as e:
            logger.error(f"✗ Check timer failed: {e}")
            dispatcher.utter_message(text="टाइमर check नहीं हो सका")
            return []


class ActionAddToShoppingList(Action):
    """Add item to shopping list"""
    
    def name(self) -> Text:
        return "action_add_to_shopping_list"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        item = tracker.get_slot("shopping_item")
        
        if not item:
            dispatcher.utter_message(text="क्या add करना है?")
            return []
        
        try:
            # Save to database
            db = get_db()
            item_id = db.add_shopping_item(item)
            
            response = f"'{item}' शॉपिंग लिस्ट में डाल दिया"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Shopping list add: {item} (ID: {item_id})")
            
            return [SlotSet("context_item", item)]
        
        except Exception as e:
            logger.error(f"✗ Add to shopping list failed: {e}")
            dispatcher.utter_message(text="item add नहीं हो सका")
            return []


class ActionRemoveFromShoppingList(Action):
    """Remove item from shopping list"""
    
    def name(self) -> Text:
        return "action_remove_from_shopping_list"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        item = tracker.get_slot("shopping_item") or tracker.get_slot("context_item")
        
        if not item:
            dispatcher.utter_message(text="क्या हटाना है?")
            return []
        
        try:
            db = get_db()
            db.remove_shopping_item(item)
            
            response = f"'{item}' लिस्ट से हटा दिया"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Shopping list remove: {item}")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Remove from shopping list failed: {e}")
            dispatcher.utter_message(text="item हटा नहीं सके")
            return []


class ActionReadShoppingList(Action):
    """Read shopping list"""
    
    def name(self) -> Text:
        return "action_read_shopping_list"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            db = get_db()
            items = db.get_shopping_list()
            
            if not items:
                response = "शॉपिंग लिस्ट खाली है"
            else:
                item_names = [item['item'] for item in items]
                
                if len(item_names) == 1:
                    response = f"शॉपिंग लिस्ट में है: {item_names[0]}"
                elif len(item_names) <= 5:
                    item_list = ", ".join(item_names)
                    response = f"शॉपिंग लिस्ट में हैं: {item_list}"
                else:
                    # Too many items, give count
                    first_five = ", ".join(item_names[:5])
                    response = f"शॉपिंग लिस्ट में {len(item_names)} items हैं। पहले 5: {first_five}"
            
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Read shopping list: {len(items)} items")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Read shopping list failed: {e}")
            dispatcher.utter_message(text="लिस्ट पढ़ नहीं सके")
            return []


class ActionClearShoppingList(Action):
    """Clear entire shopping list"""
    
    def name(self) -> Text:
        return "action_clear_shopping_list"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            db = get_db()
            db.clear_shopping_list()
            
            # Publish to MQTT
            mqtt_pub.publish("list/shopping/clear", {
                "timestamp": datetime.now().isoformat()
            })
            
            response = "शॉपिंग लिस्ट खाली कर दी"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Shopping list cleared")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Clear shopping list failed: {e}")
            dispatcher.utter_message(text="लिस्ट clear नहीं हो सकी")
            return []


# ==================== TODO LIST ACTIONS ====================

class ActionAddToTodo(Action):
    """Add task to todo list"""
    
    def name(self) -> Text:
        return "action_add_to_todo"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        item = tracker.get_slot("todo_item")
        
        if not item:
            dispatcher.utter_message(text="कौन सा काम add करना है?")
            return []
        
        try:
            # Save to database
            db = get_db()
            todo_id = db.add_todo(item)
            
            # Publish to MQTT
            mqtt_pub.publish("list/todo/add", {
                "id": todo_id,
                "task": item,
                "timestamp": datetime.now().isoformat()
            })
            
            response = f"'{item}' टू-डू लिस्ट में डाल दिया"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Todo add: {item} (ID: {todo_id})")
            
            return [SlotSet("context_item", item)]
        
        except Exception as e:
            logger.error(f"✗ Add to todo failed: {e}")
            dispatcher.utter_message(text="task add नहीं हो सका")
            return []


class ActionMarkTodoComplete(Action):
    """Mark todo item as complete"""
    
    def name(self) -> Text:
        return "action_mark_todo_complete"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        item = tracker.get_slot("todo_item") or tracker.get_slot("context_item")
        
        if not item:
            dispatcher.utter_message(text="कौन सा काम complete हुआ?")
            return []
        
        try:
            db = get_db()
            db.mark_todo_complete(task=item)
            
            # Publish to MQTT
            mqtt_pub.publish("list/todo/complete", {
                "task": item,
                "timestamp": datetime.now().isoformat()
            })
            
            response = f"'{item}' complete कर दिया"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Todo completed: {item}")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Mark todo complete failed: {e}")
            dispatcher.utter_message(text="task complete नहीं कर सके")
            return []


class ActionReadTodoList(Action):
    """Read todo list"""
    
    def name(self) -> Text:
        return "action_read_todo_list"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            db = get_db()
            todos = db.get_todo_list()
            
            if not todos:
                response = "टू-डू लिस्ट खाली है"
            else:
                task_names = [todo['task'] for todo in todos]
                
                if len(task_names) == 1:
                    response = f"आज का काम: {task_names[0]}"
                elif len(task_names) <= 5:
                    task_list = ", ".join(task_names)
                    response = f"आज के काम: {task_list}"
                else:
                    first_five = ", ".join(task_names[:5])
                    response = f"आज के {len(task_names)} काम हैं। पहले 5: {first_five}"
            
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Read todo list: {len(todos)} tasks")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Read todo list failed: {e}")
            dispatcher.utter_message(text="लिस्ट पढ़ नहीं सके")
            return []


# ==================== CALENDAR ACTIONS ====================

class ActionAddCalendarEvent(Action):
    def name(self) -> Text:
        return "action_add_calendar_event"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        event_name = tracker.get_slot("event_name")
        
        # FIX: Extract ISO string from Duckling
        event_datetime_entity = tracker.get_slot("event_time")
        event_datetime_iso = extract_duckling_value(event_datetime_entity)
        
        if not event_name:
            dispatcher.utter_message(text="कौन सा इवेंट add करना है?")
            return []
        
        # Default to tomorrow if no datetime
        if not event_datetime_iso:
            event_datetime_iso = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0).isoformat()
        
        try:
            db = get_db()
            event_id = db.add_calendar_event(
                event_name=event_name,
                event_datetime=event_datetime_iso
            )
            
            mqtt_pub.publish("calendar/add", {
                "id": event_id,
                "name": event_name,
                "datetime": event_datetime_iso,
                "timestamp": datetime.now().isoformat()
            })
            
            time_str = format_time_hindi(event_datetime_iso)
            response = f"'{event_name}' {time_str} को calendar में डाल दिया"
            
            dispatcher.utter_message(text=response)
            logger.info(f"✓ Calendar event added: {event_name} at {event_datetime_iso}")
            
            return [
                SlotSet("event_name", event_name),
                SlotSet("time", event_datetime_iso)
            ]
        
        except Exception as e:
            logger.error(f"✗ Add calendar event failed: {e}")
            dispatcher.utter_message(text="इवेंट add नहीं हो सका")
            return []

class ActionCheckCalendar(Action):
    """Check calendar events"""
    
    def name(self) -> Text:
        return "action_check_calendar"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        event_date = tracker.get_slot("event_date")
        
        try:
            db = get_db()
            
            # Parse date
            if event_date:
                if event_date in ['today', 'आज']:
                    target_date = datetime.now().date().isoformat()
                elif event_date in ['tomorrow', 'कल']:
                    target_date = (datetime.now() + timedelta(days=1)).date().isoformat()
                else:
                    target_date = event_date
                
                events = db.get_calendar_events(date=target_date)
            else:
                # Get all upcoming events
                target_date = None
                events = db.get_calendar_events()
            
            if not events:
                if target_date:
                    response = f"{event_date or target_date} को कोई इवेंट नहीं है"
                else:
                    response = "कोई आने वाला इवेंट नहीं है"
            else:
                event_texts = []
                for event in events[:5]:  # Limit to 5
                    name = event['event_name']
                    time = event.get('event_time', '')
                    if time:
                        event_texts.append(f"{name} ({time} बजे)")
                    else:
                        event_texts.append(name)
                
                event_list = ", ".join(event_texts)
                
                if target_date:
                    response = f"{event_date or target_date} को: {event_list}"
                else:
                    response = f"आने वाले events: {event_list}"
            
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Calendar check: {len(events)} events found")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Check calendar failed: {e}")
            dispatcher.utter_message(text="calendar check नहीं हो सका")
            return []


class ActionDeleteCalendarEvent(Action):
    """Delete calendar event"""
    
    def name(self) -> Text:
        return "action_delete_calendar_event"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        event_name = tracker.get_slot("event_name")
        
        if not event_name:
            dispatcher.utter_message(text="कौन सा इवेंट delete करना है?")
            return []
        
        try:
            db = get_db()
            db.delete_calendar_event(event_name=event_name)
            
            # Publish to MQTT
            mqtt_pub.publish("calendar/delete", {
                "name": event_name,
                "timestamp": datetime.now().isoformat()
            })
            
            response = f"'{event_name}' calendar से हटा दिया"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Calendar event deleted: {event_name}")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Delete calendar event failed: {e}")
            dispatcher.utter_message(text="इवेंट delete नहीं हो सका")
            return []


# ==================== MEMORY & NOTES ACTIONS ====================

class ActionRememberPreference(Action):
    """Remember user preference"""
    
    def name(self) -> Text:
        return "action_remember_preference"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        room = tracker.get_slot("room")
        device = tracker.get_slot("device")
        brightness = tracker.get_slot("brightness")
        speed = tracker.get_slot("speed")
        temperature = tracker.get_slot("temperature")
        
        try:
            db = get_db()
            saved_count = 0
            
            # Save device preferences
            if room and device:
                if brightness is not None:
                    pref_key = f"{room}_{device}_brightness"
                    db.save_preference(pref_key, str(brightness), "device")
                    saved_count += 1
                
                if speed is not None:
                    pref_key = f"{room}_{device}_speed"
                    db.save_preference(pref_key, str(speed), "device")
                    saved_count += 1
                
                if temperature is not None:
                    pref_key = f"{room}_{device}_temperature"
                    db.save_preference(pref_key, str(temperature), "device")
                    saved_count += 1
            
            # Publish to MQTT
            mqtt_pub.publish("memory/preference/save", {
                "room": room,
                "device": device,
                "brightness": brightness,
                "speed": speed,
                "temperature": temperature,
                "timestamp": datetime.now().isoformat()
            })
            
            response = "ठीक है, याद रखा"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Preference saved: {room} {device} ({saved_count} settings)")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Save preference failed: {e}")
            dispatcher.utter_message(text="याद नहीं रख सके")
            return []


class ActionRecallMemory(Action):
    """Recall stored memories"""
    
    def name(self) -> Text:
        return "action_recall_memory"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        room = tracker.get_slot("room")
        device = tracker.get_slot("device")
        
        try:
            db = get_db()
            
            # Try to recall device preferences
            if room and device:
                prefs = []
                
                # Check for brightness
                brightness = db.get_preference(f"{room}_{device}_brightness")
                if brightness:
                    prefs.append(f"brightness {brightness}%")
                
                # Check for speed
                speed = db.get_preference(f"{room}_{device}_speed")
                if speed:
                    prefs.append(f"स्पीड {speed}")
                
                # Check for temperature
                temp = db.get_preference(f"{room}_{device}_temperature")
                if temp:
                    prefs.append(f"temperature {temp}°")
                
                if prefs:
                    pref_text = ", ".join(prefs)
                    response = f"{room} की {device} के लिए: {pref_text}"
                else:
                    response = f"{room} की {device} के लिए कोई preference याद नहीं है"
            else:
                # General memory recall
                response = "क्या याद दिलाना है?"
            
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Memory recall: {room} {device}")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Recall memory failed: {e}")
            dispatcher.utter_message(text="याद नहीं आ रहा")
            return []


class ActionForgetMemory(Action):
    """Forget something"""
    
    def name(self) -> Text:
        return "action_forget_memory"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        room = tracker.get_slot("room")
        device = tracker.get_slot("device")
        
        try:
            db = get_db()
            
            # If specific device mentioned, forget those preferences
            if room and device:
                db.forget_memory(f"{room}_{device}_brightness")
                db.forget_memory(f"{room}_{device}_speed")
                db.forget_memory(f"{room}_{device}_temperature")
                
                response = f"{room} की {device} की preferences भूल गया"
            else:
                # General forget
                response = "ठीक है, भूल गया"
            
            # Publish to MQTT
            mqtt_pub.publish("memory/forget", {
                "room": room,
                "device": device,
                "timestamp": datetime.now().isoformat()
            })
            
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Memory forgotten: {room} {device}")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Forget memory failed: {e}")
            dispatcher.utter_message(text="भूल नहीं सके")
            return []


class ActionCreateNote(Action):
    """Create a note"""
    
    def name(self) -> Text:
        return "action_create_note"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        note_content = tracker.get_slot("note_content")
        
        if not note_content:
            dispatcher.utter_message(text="क्या note करना है?")
            return []
        
        try:
            # Save to database
            db = get_db()
            note_id = db.add_note(note_content)
            
            # Publish to MQTT
            mqtt_pub.publish("memory/note/add", {
                "id": note_id,
                "content": note_content[:100],  # Truncate for MQTT
                "timestamp": datetime.now().isoformat()
            })
            
            response = "नोट सेव कर दिया"
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Note created: {note_content[:50]}... (ID: {note_id})")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Create note failed: {e}")
            dispatcher.utter_message(text="नोट save नहीं हो सका")
            return []


class ActionReadNotes(Action):
    """Read recent notes"""
    
    def name(self) -> Text:
        return "action_read_notes"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            db = get_db()
            notes = db.get_notes(limit=5)
            
            if not notes:
                response = "कोई notes नहीं हैं"
            else:
                note_count = len(notes)
                
                if note_count == 1:
                    note_text = notes[0]['content'][:100]  # Truncate long notes
                    response = f"आपका 1 note: {note_text}"
                else:
                    response = f"आपके पास {note_count} notes हैं"
            
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Read notes: {len(notes)} found")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Read notes failed: {e}")
            dispatcher.utter_message(text="notes पढ़ नहीं सके")
            return []


class ActionSearchMemory(Action):
    """Search through memories and notes"""
    
    def name(self) -> Text:
        return "action_search_memory"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get search term from last user message
        search_term = tracker.latest_message.get('text', '')
        
        # Extract key words (remove common words)
        stop_words = ['क्या', 'कहाँ', 'कब', 'कौन', 'याद', 'है', 'था', 'search', 'find']
        search_words = [w for w in search_term.split() if w.lower() not in stop_words]
        
        if not search_words:
            dispatcher.utter_message(text="क्या search करना है?")
            return []
        
        try:
            db = get_db()
            
            # Search in notes
            notes = db.search_notes(search_words[0])
            
            # Search in memories
            memories = db.search_memories(search_words[0])
            
            results_count = len(notes) + len(memories)
            
            if results_count == 0:
                response = "कुछ नहीं मिला"
            elif results_count == 1:
                if notes:
                    content = notes[0]['content'][:100]
                    response = f"मिला: {content}"
                else:
                    value = memories[0]['memory_value']
                    response = f"मिला: {value}"
            else:
                response = f"{results_count} चीज़ें मिलीं"
            
            dispatcher.utter_message(text=response)
            
            logger.info(f"✓ Memory search: '{search_words[0]}' - {results_count} results")
            
            return []
        
        except Exception as e:
            logger.error(f"✗ Search memory failed: {e}")
            dispatcher.utter_message(text="search नहीं हो सका")
            return []