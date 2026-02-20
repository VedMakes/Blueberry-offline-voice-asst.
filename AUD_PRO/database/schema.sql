-- -- Create tables for assistant data

-- -- Alarms
-- CREATE TABLE IF NOT EXISTS alarms (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     time TEXT NOT NULL,
--     name TEXT,
--     enabled INTEGER DEFAULT 1,
--     repeat_days TEXT,  -- JSON: ["monday", "wednesday"]
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     user_id TEXT DEFAULT 'default'
-- );

-- -- Reminders
-- CREATE TABLE IF NOT EXISTS reminders (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     reminder_time TEXT NOT NULL,
--     reminder_text TEXT NOT NULL,
--     completed INTEGER DEFAULT 0,
--     notified INTEGER DEFAULT 0,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     user_id TEXT DEFAULT 'default'
-- );

-- -- Timers
-- CREATE TABLE IF NOT EXISTS timers (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     duration_seconds INTEGER NOT NULL,
--     start_time TIMESTAMP NOT NULL,
--     name TEXT,
--     active INTEGER DEFAULT 1,
--     user_id TEXT DEFAULT 'default'
-- );

-- -- Shopping List
-- CREATE TABLE IF NOT EXISTS shopping_list (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     item TEXT NOT NULL,
--     quantity TEXT,
--     category TEXT,
--     checked INTEGER DEFAULT 0,
--     added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     user_id TEXT DEFAULT 'default'
-- );

-- -- Todo List
-- CREATE TABLE IF NOT EXISTS todo_list (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     task TEXT NOT NULL,
--     completed INTEGER DEFAULT 0,
--     priority TEXT DEFAULT 'medium',  -- low, medium, high
--     due_date TEXT,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     user_id TEXT DEFAULT 'default'
-- );

-- -- Notes
-- CREATE TABLE IF NOT EXISTS notes (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     title TEXT,
--     content TEXT NOT NULL,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     user_id TEXT DEFAULT 'default'
-- );

-- -- Calendar Events
-- CREATE TABLE IF NOT EXISTS calendar_events (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     event_name TEXT NOT NULL,
--     event_date TEXT NOT NULL,
--     event_time TEXT,
--     location TEXT,
--     description TEXT,
--     reminder_minutes INTEGER,  -- Remind X minutes before
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     user_id TEXT DEFAULT 'default'
-- );

-- -- User Preferences (device settings, favorite configurations)
-- CREATE TABLE IF NOT EXISTS preferences (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     preference_key TEXT NOT NULL,
--     preference_value TEXT NOT NULL,
--     category TEXT,  -- 'device', 'room', 'general'
--     user_id TEXT DEFAULT 'default',
--     UNIQUE(preference_key, user_id)
-- );

-- -- Memory/Context (things user asked to remember)
-- CREATE TABLE IF NOT EXISTS memories (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     memory_type TEXT,  -- 'fact', 'preference', 'instruction'
--     memory_key TEXT,
--     memory_value TEXT NOT NULL,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     user_id TEXT DEFAULT 'default'
-- );

-- -- Device States (last known state of devices)
-- CREATE TABLE IF NOT EXISTS device_states (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     room TEXT NOT NULL,
--     device TEXT NOT NULL,
--     state TEXT NOT NULL,  -- 'on', 'off'
--     brightness INTEGER,
--     speed TEXT,
--     temperature INTEGER,
--     last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     UNIQUE(room, device)
-- );

-- -- Create indexes for better query performance
-- CREATE INDEX IF NOT EXISTS idx_alarms_time ON alarms(time);
-- CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(reminder_time);
-- CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_events(event_date);
-- CREATE INDEX IF NOT EXISTS idx_shopping_checked ON shopping_list(checked);
-- CREATE INDEX IF NOT EXISTS idx_todo_completed ON todo_list(completed);


-- Alarms
CREATE TABLE IF NOT EXISTS alarms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alarm_datetime TEXT NOT NULL,  -- ISO 8601: "2026-02-14T17:00:00+05:30"
    name TEXT,
    enabled INTEGER DEFAULT 1,
    repeat_days TEXT,  -- JSON: ["monday", "wednesday"]
    created_at TEXT DEFAULT (datetime('now')),
    user_id TEXT DEFAULT 'default'
);

-- Reminders
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reminder_datetime TEXT NOT NULL,  -- ISO 8601: "2026-02-14T15:30:00+05:30"
    reminder_text TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    notified INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    user_id TEXT DEFAULT 'default'
);

-- Timers
CREATE TABLE IF NOT EXISTS timers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    duration_seconds INTEGER NOT NULL,
    start_datetime TEXT NOT NULL,  -- ISO 8601
    end_datetime TEXT NOT NULL,     -- ISO 8601 (calculated: start + duration)
    name TEXT,
    active INTEGER DEFAULT 1,
    user_id TEXT DEFAULT 'default'
);

-- Shopping List (unchanged - no time parsing needed)
CREATE TABLE IF NOT EXISTS shopping_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL,
    quantity TEXT,
    category TEXT,
    checked INTEGER DEFAULT 0,
    added_at TEXT DEFAULT (datetime('now')),
    user_id TEXT DEFAULT 'default'
);

-- Todo List
CREATE TABLE IF NOT EXISTS todo_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    priority TEXT DEFAULT 'medium',  -- low, medium, high
    due_datetime TEXT,  -- ISO 8601 (optional)
    created_at TEXT DEFAULT (datetime('now')),
    user_id TEXT DEFAULT 'default'
);

-- Notes (unchanged)
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    user_id TEXT DEFAULT 'default'
);

-- Calendar Events
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    event_datetime TEXT NOT NULL,  -- ISO 8601: "2026-02-15T14:30:00+05:30"
    location TEXT,
    description TEXT,
    reminder_minutes INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    user_id TEXT DEFAULT 'default'
);

-- User Preferences (unchanged)
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preference_key TEXT NOT NULL,
    preference_value TEXT NOT NULL,
    category TEXT,  -- 'device', 'room', 'general'
    user_id TEXT DEFAULT 'default',
    UNIQUE(preference_key, user_id)
);

-- Memory/Context (unchanged)
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_type TEXT,  -- 'fact', 'preference', 'instruction'
    memory_key TEXT,
    memory_value TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    user_id TEXT DEFAULT 'default'
);

-- Device States (unchanged)
CREATE TABLE IF NOT EXISTS device_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room TEXT NOT NULL,
    device TEXT NOT NULL,
    state TEXT NOT NULL,  -- 'on', 'off'
    brightness INTEGER,
    speed TEXT,
    temperature INTEGER,
    last_updated TEXT DEFAULT (datetime('now')),
    UNIQUE(room, device)
);

-- Usage Patterns (NEW - for proactive suggestions)
CREATE TABLE IF NOT EXISTS usage_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room TEXT NOT NULL,
    device TEXT NOT NULL,
    action TEXT NOT NULL,  -- 'turn_on', 'turn_off', etc.
    timetamp TEXT NOT NULL,  -- ISO 8601
    user_id TEXT DEFAULT 'default'
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_alarms_datetime ON alarms(alarm_datetime);
CREATE INDEX IF NOT EXISTS idx_reminders_datetime ON reminders(reminder_datetime);
CREATE INDEX IF NOT EXISTS idx_timers_end ON timers(end_datetime);
CREATE INDEX IF NOT EXISTS idx_calendar_datetime ON calendar_events(event_datetime);
CREATE INDEX IF NOT EXISTS idx_shopping_checked ON shopping_list(checked);
CREATE INDEX IF NOT EXISTS idx_todo_completed ON todo_list(completed);
CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_patterns(timetamp);
CREATE INDEX IF NOT EXISTS idx_device_updated ON device_states(last_updated);