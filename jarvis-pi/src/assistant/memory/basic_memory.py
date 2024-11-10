import sqlite3
import logging
from datetime import datetime
from threading import Lock, RLock
from contextlib import contextmanager

class BasicMemory:
    def __init__(self, db_path="semantic_memory.db"):
        """Initialize SQLite memory system"""
        self.db_path = db_path
        self.write_lock = Lock()
        self.read_lock = RLock()
        self.setup_database()

    @contextmanager
    def get_db_connection(self, for_writing=False):
        """Thread-safe database connection manager"""
        lock = self.write_lock if for_writing else self.read_lock
        with lock:
            conn = sqlite3.connect(self.db_path)
            try:
                yield conn
                if for_writing:
                    conn.commit()
            except Exception as e:
                if for_writing:
                    conn.rollback()
                raise e
            finally:
                conn.close()

    def setup_database(self):
        """Create the interactions table if it doesn't exist"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        user_message TEXT,
                        assistant_response TEXT,
                        timestamp DATETIME
                    )
                ''')
        except sqlite3.Error as e:
            logging.error(f"Database setup error: {e}")

    def add_interaction(self, user_id, user_message, assistant_response):
        """Store a new interaction in the database"""
        try:
            with self.get_db_connection(for_writing=True) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO interactions 
                    (user_id, user_message, assistant_response, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, user_message, assistant_response, datetime.now()))
        except sqlite3.Error as e:
            logging.error(f"Error adding interaction: {e}")

    def get_recent_interactions(self, limit=5):
        """Get the most recent interactions"""
        try:
            with self.get_db_connection(for_writing=False) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_message, assistant_response, timestamp 
                    FROM interactions 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error retrieving interactions: {e}")
            return []

    def search_interactions(self, query):
        """Search interactions for specific text"""
        try:
            with self.get_db_connection(for_writing=False) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_message, assistant_response, timestamp 
                    FROM interactions 
                    WHERE user_message LIKE ? OR assistant_response LIKE ?
                    ORDER BY timestamp DESC
                ''', (f'%{query}%', f'%{query}%'))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error searching interactions: {e}")
            return []

    def get_interaction_count(self):
        """Get total number of interactions"""
        try:
            with self.get_db_connection(for_writing=False) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM interactions')
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logging.error(f"Error counting interactions: {e}")
            return 0