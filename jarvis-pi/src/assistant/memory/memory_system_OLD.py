from abc import ABC, abstractmethod
from datetime import datetime
import sqlite3
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

important_information = {
    "Primary user": ["name", "age", "gender", "interests", "goals", "preferences"],
    "Family": ["names", "ages", "relationships"],
    "Friends": ["names", "ages", "relationships"],
    "Work": ["names", "roles", "responsibilities"],
    "Home": ["address", "floorplan", "important locations"],
}

@dataclass
class MemoryEntry:
    """Base class for memory entries"""
    timestamp: datetime
    content: str
    metadata: Dict[str, Any]

class BaseMemoryStore(ABC):
    """Abstract base class for memory stores"""
    
    @abstractmethod
    def add(self, entry: MemoryEntry) -> None:
        """Add a new memory entry"""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search for memory entries"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup old entries based on store-specific rules"""
        pass

class SQLiteMemoryStore(BaseMemoryStore):
    def __init__(self, db_path: str, table_name: str, max_age_days: Optional[int] = None):
        self.db_path = db_path
        self.table_name = table_name
        self.max_age_days = max_age_days
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            # Create index for faster searching
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_timestamp ON {self.table_name}(timestamp)")
    
    def add(self, entry: MemoryEntry) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"INSERT INTO {self.table_name} (timestamp, content, metadata) VALUES (?, ?, ?)",
                (entry.timestamp.isoformat(), entry.content, json.dumps(entry.metadata))
            )
    
    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"""
                SELECT timestamp, content, metadata 
                FROM {self.table_name}
                WHERE content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (f"%{query}%", limit)
            )
            
            return [
                MemoryEntry(
                    timestamp=datetime.fromisoformat(row[0]),
                    content=row[1],
                    metadata=json.loads(row[2])
                )
                for row in cursor.fetchall()
            ]
    
    def cleanup(self) -> None:
        if self.max_age_days is not None:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"""
                    DELETE FROM {self.table_name}
                    WHERE timestamp < datetime('now', '-{self.max_age_days} days')
                    """
                )

class MemorySystem:
    """Main memory system that manages both short-term and long-term memory"""
    
    def __init__(
        self,
        short_term_store: BaseMemoryStore,
        long_term_store: BaseMemoryStore,
        short_term_to_long_term_threshold: int = 30  # days
    ):
        self.short_term_store = short_term_store
        self.long_term_store = long_term_store
        self.threshold = short_term_to_long_term_threshold
    
    def add_memory(self, content: str, metadata: Dict[str, Any] = None) -> None:
        """Add a new memory to short-term storage"""
        entry = MemoryEntry(
            timestamp=datetime.now(),
            content=content,
            metadata=metadata or {}
        )
        self.short_term_store.add(entry)
    
    def search_memories(self, query: str, include_long_term: bool = True) -> List[MemoryEntry]:
        """Search both memory stores, prioritizing short-term memories"""
        results = self.short_term_store.search(query)
        
        if include_long_term:
            long_term_results = self.long_term_store.search(query)
            # Combine results, removing duplicates based on content
            seen_content = {entry.content for entry in results}
            results.extend([entry for entry in long_term_results if entry.content not in seen_content])
        
        return results
    
    def maintain(self) -> None:
        """Perform maintenance tasks like cleaning up old memories and moving memories between stores"""
        # Clean up both stores
        self.short_term_store.cleanup()
        self.long_term_store.cleanup()
        
        # Move old short-term memories to long-term storage
        threshold_date = datetime.now().timestamp() - (self.threshold * 24 * 3600)
        old_memories = self.short_term_store.search(
            query="",  # Empty query to get all entries
            limit=1000  # Adjust based on your needs
        )
        
        for memory in old_memories:
            if memory.timestamp.timestamp() < threshold_date:
                # Create a summarized version for long-term storage
                summarized_content = f"Summary: {memory.content[:200]}..."  # Simple summarization
                self.long_term_store.add(MemoryEntry(
                    timestamp=memory.timestamp,
                    content=summarized_content,
                    metadata=memory.metadata
                ))

# Example usage
def create_memory_system(
    short_term_db_path: str = "short_term.db",
    long_term_db_path: str = "long_term.db"
) -> MemorySystem:
    """Create a new memory system with SQLite stores"""
    short_term = SQLiteMemoryStore(
        db_path=short_term_db_path,
        table_name="memories",
        max_age_days=30  # Keep memories for 30 days in short-term
    )
    
    long_term = SQLiteMemoryStore(
        db_path=long_term_db_path,
        table_name="memories",
        max_age_days=365  # Keep memories for 1 year in long-term
    )
    
    return MemorySystem(short_term, long_term)