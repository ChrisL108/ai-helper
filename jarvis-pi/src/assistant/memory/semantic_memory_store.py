from typing import List, Dict, Any, Optional
import sqlite3
import json
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
from contextlib import contextmanager

class SemanticMemoryStore:
    def __init__(self, db_path: str = "semantic_memory.db"):
        self.db_path = db_path
        # Load the sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self._initialize_db()

    def _initialize_db(self):
        """Initialize the database with tables for semantic search."""
        with self._get_connection() as conn:
            # Main memories table with embeddings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    category TEXT,
                    timestamp TIMESTAMP,
                    metadata TEXT,
                    confidence FLOAT
                )
            """)
            
            # Create an index for faster category searches
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_category 
                ON memories(category)
            """)
    
    @contextmanager
    def _get_connection(self):
        """Database connection context manager."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def store_memory(self, content: str, category: str = "general", 
                    metadata: Dict = None, confidence: float = 1.0) -> int:
        """
        Store a new memory with its semantic embedding.
        Returns the ID of the stored memory.
        """
        # Generate embedding for the content
        embedding = self.model.encode(content)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO memories 
                (content, embedding, category, timestamp, metadata, confidence)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """, (
                content,
                embedding.tobytes(),
                category,
                json.dumps(metadata or {}),
                confidence
            ))
            return cursor.lastrowid

    def search_memories(self, query: str, limit: int = 5, 
                       min_similarity: float = 0.5, 
                       category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search memories using semantic similarity.
        Returns memories ordered by relevance.
        """
        # Generate embedding for the query
        query_embedding = self.model.encode(query)
        
        with self._get_connection() as conn:
            # Get all relevant memories
            if category:
                cursor = conn.execute("SELECT * FROM memories WHERE category = ?", (category,))
            else:
                cursor = conn.execute("SELECT * FROM memories")
            
            results = []
            for row in cursor:
                # Convert stored embedding back to numpy array
                stored_embedding = np.frombuffer(row['embedding'])
                
                # Calculate cosine similarity
                similarity = np.dot(query_embedding, stored_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
                )
                
                # Only include results above similarity threshold
                if similarity >= min_similarity:
                    results.append({
                        'id': row['id'],
                        'content': row['content'],
                        'category': row['category'],
                        'timestamp': row['timestamp'],
                        'metadata': json.loads(row['metadata']),
                        'confidence': row['confidence'],
                        'relevance': float(similarity)
                    })
            
            # Sort by relevance and return top results
            results.sort(key=lambda x: x['relevance'], reverse=True)
            return results[:limit]

    def get_memory_by_id(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", 
                (memory_id,)
            ).fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'content': row['content'],
                    'category': row['category'],
                    'timestamp': row['timestamp'],
                    'metadata': json.loads(row['metadata']),
                    'confidence': row['confidence']
                }
            return None

    def batch_store_memories(self, memories: List[Dict[str, Any]]) -> List[int]:
        """Store multiple memories efficiently."""
        ids = []
        with self._get_connection() as conn:
            for memory in memories:
                embedding = self.model.encode(memory['content'])
                cursor = conn.execute("""
                    INSERT INTO memories 
                    (content, embedding, category, timestamp, metadata, confidence)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
                """, (
                    memory['content'],
                    embedding.tobytes(),
                    memory.get('category', 'general'),
                    json.dumps(memory.get('metadata', {})),
                    memory.get('confidence', 1.0)
                ))
                ids.append(cursor.lastrowid)
        return ids

# Example usage
if __name__ == "__main__":
    memory = SemanticMemoryStore()
    
    # Store some test memories
    memories = [
        {
            'content': "User prefers to be called 'Alex' rather than 'Alexander'",
            'category': 'preferences',
            'metadata': {'source': 'direct_statement'}
        },
        {
            'content': "User has a dog named Max who is a golden retriever",
            'category': 'personal',
            'metadata': {'source': 'conversation'}
        },
        {
            'content': "User is allergic to peanuts and has an EpiPen",
            'category': 'health',
            'metadata': {'source': 'direct_statement', 'importance': 'high'}
        }
    ]
    
    memory.batch_store_memories(memories)
    
    # Example searches
    print("\nSearching for pet-related memories:")
    pet_results = memory.search_memories("What pets does the user have?")
    for result in pet_results:
        print(f"Relevance: {result['relevance']:.2f}")
        print(f"Content: {result['content']}")
        print(f"Category: {result['category']}")
        print()
    
    print("\nSearching for health-related memories:")
    health_results = memory.search_memories(
        "What should I know about the user's health?",
        category="health"
    )
    for result in health_results:
        print(f"Relevance: {result['relevance']:.2f}")
        print(f"Content: {result['content']}")
        print(f"Metadata: {result['metadata']}")
        print()
        
        

"""This solution is great for AI assistants because:

Natural Language Queries

---- Instead of exact matches like:
memory.find("allergic to peanuts")

# You can ask natural questions like:
memory.search_memories("What food allergies does the user have?")
memory.search_memories("What should I know about dietary restrictions?")
# Both would find the peanut allergy information

Confidence and Verification

---- Each memory has:
- Confidence score (how sure we are)
- Metadata (source, importance, etc.)
- Timestamp (when we learned it)
- Category (type of information)

# Makes it easy to verify information:
results = memory.search_memories("What allergies?")
for result in results:
    if result['confidence'] > 0.9 and result['metadata']['importance'] == 'high':
        # High confidence, important information

Contextual Understanding

---- The same memory can be found through different contexts:
memory.search_memories("What's the user's nickname?")
memory.search_memories("How should I address the user?")
# Both would find the 'Alex' preference

Easy Categorization

---- You can search within specific categories:
health_info = memory.search_memories(
    "What should I know?",
    category="health"
)
preferences = memory.search_memories(
    "What does the user like?",
    category="preferences"
)
For thorough checking, you can:

Search across multiple categories
Use different phrasings of the same query
Check confidence scores and metadata
Verify timestamps for most recent information
Cross-reference related memories

Would you like me to:

Add more verification features?
Show how to handle contradictory memories?
Add memory updating/correction capabilities?
Add memory importance ranking?
"""