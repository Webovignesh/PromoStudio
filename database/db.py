import sqlite3, os
from flask import g

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'promo_tool.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS shows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    folder_path TEXT,
    total_episodes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id INTEGER,
    episode_number INTEGER,
    title TEXT,
    file_path TEXT UNIQUE,
    duration_seconds REAL DEFAULT 0,
    analysis_status TEXT DEFAULT 'pending',
    analysis_progress INTEGER DEFAULT 0,
    analysis_message TEXT DEFAULT '',
    scene_data TEXT DEFAULT '[]',
    highlight_scenes TEXT DEFAULT '[]',
    ai_treatment TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(show_id) REFERENCES shows(id)
);
CREATE TABLE IF NOT EXISTS clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER,
    label TEXT DEFAULT '',
    in_point REAL NOT NULL,
    out_point REAL NOT NULL,
    duration REAL,
    scene_tag TEXT DEFAULT '',
    tag_confidence REAL DEFAULT 0,
    needs_review INTEGER DEFAULT 0,
    energy_score REAL DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(episode_id) REFERENCES episodes(id)
);
CREATE TABLE IF NOT EXISTS promos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id INTEGER,
    episode_id INTEGER,
    treatment_type TEXT NOT NULL,
    title TEXT DEFAULT '',
    target_duration REAL DEFAULT 30,
    inputs TEXT DEFAULT '{}',
    plan TEXT DEFAULT '{}',
    status TEXT DEFAULT 'draft',
    pipeline_log TEXT DEFAULT '[]',
    output_path TEXT DEFAULT '',
    final_duration REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Migration: add new columns to existing DBs without blowing away data
MIGRATIONS = [
    "ALTER TABLE episodes ADD COLUMN analysis_message TEXT DEFAULT ''",
    "ALTER TABLE episodes ADD COLUMN highlight_scenes TEXT DEFAULT '[]'",
]

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    # Run migrations safely (ignore if column already exists)
    for sql in MIGRATIONS:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            pass
    conn.close()
