"""
Time Daemon - Background service for time-based tasks
Handles alarms, timers, reminders, and calendar notifications
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import paho.mqtt.client as mqtt
from database.db_manager import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimeDaemon:
    """Background daemon for time-based tasks"""
    
    def __init__(self, mqtt_broker="localhost", mqtt_port=1883):
        self.db = get_db()
        
        # MQTT setup
        self.mqtt_client = mqtt.Client(client_id="time_daemon")
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(mqtt_broker, mqtt_port, 60)
        self.mqtt_client.loop_start()
        
        # Track triggered items to avoid duplicates
        self.triggered_alarms = set()
        self.triggered_reminders = set()
        self.triggered_events = set()
        
        # Active timers tracking
        self.active_timers = {}
        
        logger.info("Time Daemon initialized")
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Time Daemon connected to MQTT")
            
            # Subscribe to alarm/timer control topics
            client.subscribe("alarm/set")
            client.subscribe("alarm/cancel")
            client.subscribe("timer/set")
            client.subscribe("timer/cancel")
            
            # Publish status
            client.publish("system/status", json.dumps({
                "service": "time_daemon",
                "status": "ready",
                "timestamp": time.time()
            }))
        else:
            logger.error(f"Time Daemon MQTT connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        """Handle MQTT messages"""
        try:
            data = json.loads(msg.payload)
            
            if msg.topic == "timer/set":
                self.handle_timer_set(data)
            elif msg.topic == "timer/cancel":
                self.handle_timer_cancel(data)
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def handle_timer_set(self, data):
        """Handle timer set event"""
        timer_id = data.get('id')
        duration = data.get('duration_seconds')
        
        if timer_id and duration:
            end_time = datetime.now() + timedelta(seconds=duration)
            self.active_timers[timer_id] = {
                'end_time': end_time,
                'name': data.get('name'),
                'duration': duration
            }
            logger.info(f"Timer {timer_id} tracked: {duration}s")
    
    def handle_timer_cancel(self, data):
        """Handle timer cancel event"""
        timer_id = data.get('id')
        if timer_id and timer_id in self.active_timers:
            del self.active_timers[timer_id]
            logger.info(f"Timer {timer_id} cancelled")
    
    def check_alarms(self):
        """Check if any alarms should trigger"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # Get active alarms
        alarms = self.db.get_active_alarms()
        
        for alarm in alarms:
            alarm_id = alarm['id']
            alarm_time = alarm['alarm_datetime']
            
            # Check if alarm time matches (to the minute)
            if alarm_time == current_time:
                # Check if already triggered today
                trigger_key = f"{alarm_id}_{now.date()}"
                
                if trigger_key not in self.triggered_alarms:
                    self.trigger_alarm(alarm)
                    self.triggered_alarms.add(trigger_key)
                    
                    # Clean old triggers (keep only today's)
                    self.triggered_alarms = {
                        k for k in self.triggered_alarms 
                        if k.endswith(str(now.date()))
                    }
    
    def trigger_alarm(self, alarm: Dict):
        """Trigger an alarm"""
        alarm_time = alarm['alarm_datetime']
        alarm_name = alarm.get('name', '')
        
        # Prepare notification text
        if alarm_name:
            notification = f"अलार्म: {alarm_name}"
        else:
            notification = f"{alarm_time} बजे का अलार्म"
        
        # Publish to TTS
        self.mqtt_client.publish("tts/speak", json.dumps({
            "text": notification,
            "priority": "high",
            "timestamp": time.time()
        }))
        
        # Publish alarm triggered event
        self.mqtt_client.publish("alarm/triggered", json.dumps({
            "id": alarm['id'],
            "time": alarm_time,
            "name": alarm_name,
            "timestamp": time.time()
        }))
        
        logger.info(f"Alarm triggered: {alarm_time} - {alarm_name}")
        
        # Check if alarm should repeat
        if not alarm.get('repeat_days'):
            # One-time alarm, disable it
            self.db.cancel_alarm(alarm_id=alarm['id'])
    
    def check_timers(self):
        """Check if any timers have completed"""
        now = datetime.now()
        completed_timers = []
        
        for timer_id, timer_data in self.active_timers.items():
            if now >= timer_data['end_time']:
                completed_timers.append(timer_id)
                self.trigger_timer(timer_id, timer_data)
        
        # Remove completed timers
        for timer_id in completed_timers:
            del self.active_timers[timer_id]
            # Update database
            self.db.cancel_timer(timer_id)
    
    def trigger_timer(self, timer_id: int, timer_data: Dict):
        """Trigger a timer completion"""
        name = timer_data.get('name', '')
        
        if name:
            notification = f"टाइमर '{name}' पूरा हो गया"
        else:
            notification = "टाइमर पूरा हो गया"
        
        # Publish to TTS
        self.mqtt_client.publish("tts/speak", json.dumps({
            "text": notification,
            "priority": "high",
            "timestamp": time.time()
        }))
        
        # Publish timer completed event
        self.mqtt_client.publish("timer/completed", json.dumps({
            "id": timer_id,
            "name": name,
            "timestamp": time.time()
        }))
        
        logger.info(f"Timer completed: {timer_id} - {name}")
    
    def check_reminders(self):
        """Check if any reminders should trigger"""
        now = datetime.now()
        current_datetime = now.strftime("%Y-%m-%d %H:%M")
        
        # Get pending reminders
        reminders = self.db.get_pending_reminders()
        
        for reminder in reminders:
            reminder_id = reminder['id']
            reminder_time = reminder['reminder_time']
            
            # Check if reminder time has passed
            try:
                reminder_dt = datetime.fromisoformat(reminder_time)
                
                if now >= reminder_dt:
                    trigger_key = f"{reminder_id}"
                    
                    if trigger_key not in self.triggered_reminders:
                        self.trigger_reminder(reminder)
                        self.triggered_reminders.add(trigger_key)
                        
                        # Mark as notified in database
                        self.db.mark_reminder_notified(reminder_id)
            
            except ValueError:
                logger.error(f"Invalid reminder time format: {reminder_time}")
    
    def trigger_reminder(self, reminder: Dict):
        """Trigger a reminder"""
        reminder_text = reminder['reminder_text']
        
        notification = f"रिमाइंडर: {reminder_text}"
        
        # Publish to TTS
        self.mqtt_client.publish("tts/speak", json.dumps({
            "text": notification,
            "priority": "high",
            "timestamp": time.time()
        }))
        
        # Publish reminder triggered event
        self.mqtt_client.publish("reminder/triggered", json.dumps({
            "id": reminder['id'],
            "text": reminder_text,
            "timestamp": time.time()
        }))
        
        logger.info(f"Reminder triggered: {reminder_text}")
    
    def check_calendar_events(self):
        """Check for upcoming calendar events with reminders"""
        now = datetime.now()
        today = now.date().isoformat()
        
        # Get today's events
        events = self.db.get_calendar_events(date=today)
        
        for event in events:
            event_id = event['id']
            event_name = event['event_name']
            event_time = event.get('event_time')
            reminder_minutes = event.get('reminder_minutes')
            
            if not event_time or not reminder_minutes:
                continue
            
            try:
                # Parse event datetime
                event_datetime_str = f"{event['event_date']} {event_time}"
                event_dt = datetime.fromisoformat(event_datetime_str)
                
                # Calculate reminder time
                reminder_dt = event_dt - timedelta(minutes=reminder_minutes)
                
                # Check if it's time for reminder
                if now >= reminder_dt and now < event_dt:
                    trigger_key = f"{event_id}_{now.date()}"
                    
                    if trigger_key not in self.triggered_events:
                        self.trigger_calendar_reminder(event, reminder_minutes)
                        self.triggered_events.add(trigger_key)
                        
                        # Clean old triggers
                        self.triggered_events = {
                            k for k in self.triggered_events 
                            if k.endswith(str(now.date()))
                        }
            
            except ValueError:
                logger.error(f"Invalid event datetime: {event_datetime_str}")
    
    def trigger_calendar_reminder(self, event: Dict, minutes_before: int):
        """Trigger a calendar event reminder"""
        event_name = event['event_name']
        event_time = event['event_time']
        
        notification = f"रिमाइंडर: {minutes_before} मिनट में '{event_name}' है"
        
        # Publish to TTS
        self.mqtt_client.publish("tts/speak", json.dumps({
            "text": notification,
            "priority": "high",
            "timestamp": time.time()
        }))
        
        logger.info(f"Calendar reminder: {event_name} in {minutes_before} min")
    
    def load_existing_timers(self):
        """Load timers from database on startup"""
        timers = self.db.get_active_timers()
        
        for timer in timers:
            timer_id = timer['id']
            start_time = datetime.fromisoformat(timer['start_time'])
            duration = timer['duration_seconds']
            
            end_time = start_time + timedelta(seconds=duration)
            
            # Only load if not expired
            if datetime.now() < end_time:
                self.active_timers[timer_id] = {
                    'end_time': end_time,
                    'name': timer.get('name'),
                    'duration': duration
                }
                logger.info(f"Loaded existing timer: {timer_id}")
            else:
                # Timer expired while daemon was down
                self.db.cancel_timer(timer_id)
    
    def run(self):
        """Main daemon loop"""
        logger.info("Time Daemon started")
        
        # Load existing timers
        self.load_existing_timers()
        
        try:
            while True:
                # Check all time-based tasks
                self.check_alarms()
                self.check_timers()
                self.check_reminders()
                self.check_calendar_events()
                
                # Sleep for 1 second (can adjust based on precision needs)
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Time Daemon shutting down...")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.db.close()
        
        except Exception as e:
            logger.error(f"Fatal error in Time Daemon: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    daemon = TimeDaemon()
    daemon.run()