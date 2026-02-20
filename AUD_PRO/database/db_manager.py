import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import dateutil.parser

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages all persistent data for the voice assistant (Duckling-compatible)"""
    
    def __init__(self, db_path: str = "assistant_data.db"):
        self.db_path = db_path
        self.conn = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize database and create tables"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            
            # Enable WAL mode for better concurrency
            self.conn.execute("PRAGMA journal_mode=WAL")
            
            # Read and execute schema
            schema_path = Path(__file__).parent / "schema.sql"
            if schema_path.exists():
                with open(schema_path, 'r', encoding='utf-8') as f:
                    self.conn.executescript(f.read())
            
            logger.info(f"Database initialized: {self.db_path}")
        
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query with error handling"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor
        except Exception as e:
            logger.error(f"Query failed: {query} | Error: {e}")
            self.conn.rollback()
            raise
    
    def _fetchall(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all results as list of dicts"""
        cursor = self._execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def _fetchone(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch one result as dict"""
        cursor = self._execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ==================== ALARMS ====================
    
    def add_alarm(self, alarm_datetime: str, name: str = None, repeat_days: List[str] = None) -> int:
        """
        Add a new alarm
        
        Args:
            alarm_datetime: ISO 8601 string from Duckling (e.g., "2026-02-14T17:00:00+05:30")
            name: Optional alarm name
            repeat_days: Optional list of days ["monday", "wednesday"]
        """
        repeat_json = json.dumps(repeat_days) if repeat_days else None
        query = "INSERT INTO alarms (alarm_datetime, name, repeat_days) VALUES (?, ?, ?)"
        cursor = self._execute(query, (alarm_datetime, name, repeat_json))
        logger.info(f"Alarm added: {alarm_datetime} - {name}")
        return cursor.lastrowid
    
    def get_active_alarms(self) -> List[Dict]:
        """Get all enabled alarms"""
        query = "SELECT * FROM alarms WHERE enabled = 1 ORDER BY alarm_datetime"
        return self._fetchall(query)
    
    def get_due_alarms(self, current_datetime: str = None) -> List[Dict]:
        """
        Get alarms that should trigger now
        
        Args:
            current_datetime: ISO 8601 string (defaults to now)
        """
        if not current_datetime:
            current_datetime = datetime.now().isoformat()
        
        query = """
            SELECT * FROM alarms 
            WHERE enabled = 1 
            AND alarm_datetime <= ?
            ORDER BY alarm_datetime
        """
        return self._fetchall(query, (current_datetime,))
    
    def cancel_alarm(self, alarm_id: int = None, alarm_datetime: str = None):
        """Cancel alarm by ID or datetime"""
        if alarm_id:
            query = "DELETE FROM alarms WHERE id = ?"
            self._execute(query, (alarm_id,))
        elif alarm_datetime:
            query = "DELETE FROM alarms WHERE alarm_datetime = ?"
            self._execute(query, (alarm_datetime,))
        else:
            query = "DELETE FROM alarms"
            self._execute(query)
        
        logger.info(f"Alarm cancelled: {alarm_id or alarm_datetime or 'all'}")
    
    # ==================== REMINDERS ====================
    
    def add_reminder(self, reminder_datetime: str, reminder_text: str) -> int:
        """
        Add a new reminder
        
        Args:
            reminder_datetime: ISO 8601 string from Duckling
            reminder_text: Reminder message
        """
        query = "INSERT INTO reminders (reminder_datetime, reminder_text) VALUES (?, ?)"
        cursor = self._execute(query, (reminder_datetime, reminder_text))
        logger.info(f"Reminder added: {reminder_datetime} - {reminder_text}")
        return cursor.lastrowid
    
    def get_pending_reminders(self) -> List[Dict]:
        """Get all pending reminders"""
        query = """
            SELECT * FROM reminders 
            WHERE completed = 0 AND notified = 0 
            ORDER BY reminder_datetime
        """
        return self._fetchall(query)
    
    def get_due_reminders(self, current_datetime: str = None) -> List[Dict]:
        """Get reminders that should trigger now"""
        if not current_datetime:
            current_datetime = datetime.now().isoformat()
        
        query = """
            SELECT * FROM reminders 
            WHERE completed = 0 
            AND notified = 0
            AND reminder_datetime <= ?
            ORDER BY reminder_datetime
        """
        return self._fetchall(query, (current_datetime,))
    
    def mark_reminder_notified(self, reminder_id: int):
        """Mark reminder as notified"""
        query = "UPDATE reminders SET notified = 1 WHERE id = ?"
        self._execute(query, (reminder_id,))
    
    def cancel_reminder(self, reminder_id: int = None):
        """Cancel reminder(s)"""
        if reminder_id:
            query = "DELETE FROM reminders WHERE id = ?"
            self._execute(query, (reminder_id,))
        else:
            query = "DELETE FROM reminders WHERE completed = 0"
            self._execute(query)
        
        logger.info(f"Reminder cancelled: {reminder_id or 'all'}")
    
    # ==================== TIMERS ====================
    
    def add_timer(self, duration_seconds: int, name: str = None) -> int:
        """
        Add a new timer
        
        Args:
            duration_seconds: Timer duration in seconds
            name: Optional timer name
        """
        start_datetime = datetime.now().isoformat()
        end_datetime = (datetime.now() + timedelta(seconds=duration_seconds)).isoformat()
        
        query = """
            INSERT INTO timers (duration_seconds, start_datetime, end_datetime, name) 
            VALUES (?, ?, ?, ?)
        """
        cursor = self._execute(query, (duration_seconds, start_datetime, end_datetime, name))
        logger.info(f"Timer added: {duration_seconds}s - {name}")
        return cursor.lastrowid
    
    def get_active_timers(self) -> List[Dict]:
        """Get all active timers"""
        query = "SELECT * FROM timers WHERE active = 1"
        return self._fetchall(query)
    
    def get_completed_timers(self, current_datetime: str = None) -> List[Dict]:
        """Get timers that have completed"""
        if not current_datetime:
            current_datetime = datetime.now().isoformat()
        
        query = """
            SELECT * FROM timers 
            WHERE active = 1 
            AND end_datetime <= ?
            ORDER BY end_datetime
        """
        return self._fetchall(query, (current_datetime,))
    
    def cancel_timer(self, timer_id: int = None):
        """Cancel timer(s)"""
        if timer_id:
            query = "UPDATE timers SET active = 0 WHERE id = ?"
            self._execute(query, (timer_id,))
        else:
            query = "UPDATE timers SET active = 0"
            self._execute(query)
        
        logger.info(f"Timer cancelled: {timer_id or 'all'}")
    
    # ==================== SHOPPING LIST ====================
    
    def add_shopping_item(self, item: str, quantity: str = None, category: str = None) -> int:
        """Add item to shopping list"""
        query = "INSERT INTO shopping_list (item, quantity, category) VALUES (?, ?, ?)"
        cursor = self._execute(query, (item, quantity, category))
        logger.info(f"Shopping item added: {item}")
        return cursor.lastrowid
    
    def get_shopping_list(self, include_checked: bool = False) -> List[Dict]:
        """Get shopping list"""
        if include_checked:
            query = "SELECT * FROM shopping_list ORDER BY checked, added_at DESC"
        else:
            query = "SELECT * FROM shopping_list WHERE checked = 0 ORDER BY added_at DESC"
        return self._fetchall(query)
    
    def remove_shopping_item(self, item: str = None, item_id: int = None):
        """Remove item from shopping list"""
        if item_id:
            query = "DELETE FROM shopping_list WHERE id = ?"
            self._execute(query, (item_id,))
        elif item:
            query = "DELETE FROM shopping_list WHERE item LIKE ?"
            self._execute(query, (f"%{item}%",))
        
        logger.info(f"Shopping item removed: {item or item_id}")
    
    def clear_shopping_list(self):
        """Clear entire shopping list"""
        query = "DELETE FROM shopping_list"
        self._execute(query)
        logger.info("Shopping list cleared")
    
    # ==================== TODO LIST ====================
    
    def add_todo(self, task: str, priority: str = 'medium', due_datetime: str = None) -> int:
        """
        Add task to todo list
        
        Args:
            task: Task description
            priority: 'low', 'medium', or 'high'
            due_datetime: Optional ISO 8601 due date
        """
        query = "INSERT INTO todo_list (task, priority, due_datetime) VALUES (?, ?, ?)"
        cursor = self._execute(query, (task, priority, due_datetime))
        logger.info(f"Todo added: {task}")
        return cursor.lastrowid
    
    def get_todo_list(self, include_completed: bool = False) -> List[Dict]:
        """Get todo list"""
        if include_completed:
            query = "SELECT * FROM todo_list ORDER BY completed, priority DESC, created_at"
        else:
            query = "SELECT * FROM todo_list WHERE completed = 0 ORDER BY priority DESC, created_at"
        return self._fetchall(query)
    
    def mark_todo_complete(self, task: str = None, task_id: int = None):
        """Mark todo as complete"""
        if task_id:
            query = "UPDATE todo_list SET completed = 1 WHERE id = ?"
            self._execute(query, (task_id,))
        elif task:
            query = "UPDATE todo_list SET completed = 1 WHERE task LIKE ?"
            self._execute(query, (f"%{task}%",))
        
        logger.info(f"Todo completed: {task or task_id}")
    
    # ==================== NOTES ====================
    
    def add_note(self, content: str, title: str = None) -> int:
        """Add a note"""
        query = "INSERT INTO notes (content, title) VALUES (?, ?)"
        cursor = self._execute(query, (content, title))
        logger.info(f"Note added: {title or 'Untitled'}")
        return cursor.lastrowid
    
    def get_notes(self, limit: int = 10) -> List[Dict]:
        """Get recent notes"""
        query = "SELECT * FROM notes ORDER BY updated_at DESC LIMIT ?"
        return self._fetchall(query, (limit,))
    
    def search_notes(self, search_term: str) -> List[Dict]:
        """Search notes"""
        query = """
            SELECT * FROM notes 
            WHERE content LIKE ? OR title LIKE ? 
            ORDER BY updated_at DESC
        """
        return self._fetchall(query, (f"%{search_term}%", f"%{search_term}%"))
    
    # ==================== CALENDAR ====================
    
    def add_calendar_event(self, event_name: str, event_datetime: str,
                          location: str = None, description: str = None,
                          reminder_minutes: int = None) -> int:
        """
        Add calendar event
        
        Args:
            event_name: Event name
            event_datetime: ISO 8601 datetime from Duckling
            location: Optional location
            description: Optional description
            reminder_minutes: Remind X minutes before
        """
        query = """
            INSERT INTO calendar_events 
            (event_name, event_datetime, location, description, reminder_minutes) 
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = self._execute(query, (event_name, event_datetime, location, description, reminder_minutes))
        logger.info(f"Calendar event added: {event_name} at {event_datetime}")
        return cursor.lastrowid
    
    def get_calendar_events(self, date: str = None) -> List[Dict]:
        """
        Get calendar events
        
        Args:
            date: Optional ISO 8601 date string (e.g., "2026-02-15")
        """
        if date:
            # Get events for specific day
            query = """
                SELECT * FROM calendar_events 
                WHERE DATE(event_datetime) = DATE(?)
                ORDER BY event_datetime
            """
            return self._fetchall(query, (date,))
        else:
            # Get all upcoming events
            current_datetime = datetime.now().isoformat()
            query = """
                SELECT * FROM calendar_events 
                WHERE event_datetime >= ?
                ORDER BY event_datetime
            """
            return self._fetchall(query, (current_datetime,))
    
    def get_events_needing_reminder(self, current_datetime: str = None) -> List[Dict]:
        """Get events where reminder should trigger"""
        if not current_datetime:
            current_datetime = datetime.now().isoformat()
        
        query = """
            SELECT * FROM calendar_events 
            WHERE reminder_minutes IS NOT NULL
            AND datetime(event_datetime, '-' || reminder_minutes || ' minutes') <= ?
            AND event_datetime > ?
            ORDER BY event_datetime
        """
        return self._fetchall(query, (current_datetime, current_datetime))
    
    def delete_calendar_event(self, event_id: int = None, event_name: str = None):
        """Delete calendar event"""
        if event_id:
            query = "DELETE FROM calendar_events WHERE id = ?"
            self._execute(query, (event_id,))
        elif event_name:
            query = "DELETE FROM calendar_events WHERE event_name LIKE ?"
            self._execute(query, (f"%{event_name}%",))
        
        logger.info(f"Calendar event deleted: {event_id or event_name}")
    
    # ==================== PREFERENCES ====================
    
    def save_preference(self, key: str, value: str, category: str = 'general'):
        """Save a user preference"""
        query = """
            INSERT INTO preferences (preference_key, preference_value, category) 
            VALUES (?, ?, ?)
            ON CONFLICT(preference_key, user_id) 
            DO UPDATE SET preference_value = ?, category = ?
        """
        self._execute(query, (key, value, category, value, category))
        logger.info(f"Preference saved: {key} = {value}")
    
    def get_preference(self, key: str) -> Optional[str]:
        """Get a preference value"""
        query = "SELECT preference_value FROM preferences WHERE preference_key = ?"
        result = self._fetchone(query, (key,))
        return result['preference_value'] if result else None
    
    def get_all_preferences(self, category: str = None) -> List[Dict]:
        """Get all preferences, optionally filtered by category"""
        if category:
            query = "SELECT * FROM preferences WHERE category = ?"
            return self._fetchall(query, (category,))
        else:
            query = "SELECT * FROM preferences"
            return self._fetchall(query)
    
    # ==================== DEVICE STATES ====================
    
    def update_device_state(self, room: str, device: str, state: str,
                           brightness: int = None, speed: str = None,
                           temperature: int = None):
        """Update device state"""
        query = """
            INSERT INTO device_states 
            (room, device, state, brightness, speed, temperature, last_updated) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(room, device) 
            DO UPDATE SET 
                state = ?, 
                brightness = ?, 
                speed = ?, 
                temperature = ?,
                last_updated = ?
        """
        timestamp = datetime.now().isoformat()
        self._execute(query, (room, device, state, brightness, speed, temperature, timestamp,
                             state, brightness, speed, temperature, timestamp))
    
    def get_device_state(self, room: str, device: str) -> Optional[Dict]:
        """Get device state"""
        query = "SELECT * FROM device_states WHERE room = ? AND device = ?"
        return self._fetchone(query, (room, device))
    
    def get_all_device_states(self, room: str = None) -> List[Dict]:
        """Get all device states, optionally filtered by room"""
        if room:
            query = "SELECT * FROM device_states WHERE room = ?"
            return self._fetchall(query, (room,))
        else:
            query = "SELECT * FROM device_states"
            return self._fetchall(query)
    
    # ==================== MEMORY ====================
    
    def save_memory(self, memory_type: str, memory_key: str, memory_value: str):
        """Save a memory"""
        query = "INSERT INTO memories (memory_type, memory_key, memory_value) VALUES (?, ?, ?)"
        self._execute(query, (memory_type, memory_key, memory_value))
        logger.info(f"Memory saved: {memory_key}")
    
    def recall_memory(self, memory_key: str) -> Optional[Dict]:
        """Recall a specific memory"""
        query = "SELECT * FROM memories WHERE memory_key = ? ORDER BY created_at DESC LIMIT 1"
        return self._fetchone(query, (memory_key,))
    
    def search_memories(self, search_term: str) -> List[Dict]:
        """Search memories"""
        query = """
            SELECT * FROM memories 
            WHERE memory_key LIKE ? OR memory_value LIKE ? 
            ORDER BY created_at DESC
        """
        return self._fetchall(query, (f"%{search_term}%", f"%{search_term}%"))
    
    def forget_memory(self, memory_key: str):
        """Delete a memory"""
        query = "DELETE FROM memories WHERE memory_key = ?"
        self._execute(query, (memory_key,))
        logger.info(f"Memory forgotten: {memory_key}")
    
    # ==================== USAGE PATTERNS (NEW) ====================
    
    def log_usage(self, room: str, device: str, action: str):
        """
        Log device usage for pattern learning
        
        Args:
            room: Room name
            device: Device name
            action: Action performed ('turn_on', 'turn_off', etc.)
        """
        timestamp = datetime.now().isoformat()
        query = """
            INSERT INTO usage_patterns (room, device, action, timestamp) 
            VALUES (?, ?, ?, ?)
        """
        self._execute(query, (room, device, action, timestamp))
    
    def get_usage_patterns(self, hours_back: int = 168) -> List[Dict]:
        """
        Get usage patterns for last N hours (default: 1 week)
        """
        cutoff = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        query = """
            SELECT * FROM usage_patterns 
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """
        return self._fetchall(query, (cutoff,))
    
    # ==================== UTILITY ====================
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Singleton instance
_db_instance = None

def get_db() -> DatabaseManager:
    """Get database manager singleton"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance