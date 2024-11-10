from typing import List, Dict, Optional, Any, Set
import sqlite3
from datetime import datetime, timedelta
import time
from dataclasses import dataclass
import numpy as np
from sentence_transformers import SentenceTransformer
import re
from collections import Counter
import json
from assistant.memory.semantic_memory_store import SemanticMemoryStore

@dataclass
class Relevance:
    CRITICAL = 1.0    # Must keep (user preferences, corrections)
    HIGH = 0.8       # Very relevant (key questions, important statements)
    MEDIUM = 0.5     # Moderately relevant (context, clarifications)
    LOW = 0.2        # Might be relevant (casual statements)
    IGNORE = 0.0     # Don't store (greetings, acknowledgments)

class IntegratedMemorySystem:
    def __init__(self, db_path=':memory:'): # in-memory db
        """
        Initialize both memory systems.
        
        Args:
            semantic_store: Instance of SemanticMemoryStore for long-term memory
            db_path: Path to the SQLite database file
        """
        self.semantic_memory_store = SemanticMemoryStore()
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
        # Load model for importance detection
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def _create_tables(self):
        """Create necessary tables in the SQLite database."""
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    timestamp REAL,
                    relevance REAL,
                    user_message TEXT,
                    assistant_response TEXT,
                    metadata TEXT
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS recent_contexts (
                    user_id TEXT,
                    interaction_id INTEGER,
                    relevance REAL,
                    FOREIGN KEY(interaction_id) REFERENCES interactions(id)
                )
            ''')

    def add_interaction(self, 
                       user_id: str,
                       user_message: str,
                       assistant_response: str,
                       relevance: float = None,
                       metadata: Optional[Dict] = None) -> None:
        """
        Store a conversation interaction, automatically detecting relevance if not provided.
        """
        # Auto-detect relevance if not provided
        if relevance is None:
            # TODO: implement relevance detection
            # relevance = self._detect_relevance(user_message, assistant_response)
            relevance = Relevance.MEDIUM
            
        timestamp = time.time()
        interaction = {
            'timestamp': timestamp,
            'relevance': relevance,
            'user_message': user_message,
            'assistant_response': assistant_response,
            'metadata': json.dumps(metadata or {})
        }
        
        # Store in SQLite
        with self.conn:
            cursor = self.conn.execute('''
                INSERT INTO interactions (user_id, timestamp, relevance, user_message, assistant_response, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, timestamp, relevance, user_message, assistant_response, interaction['metadata']))
            interaction_id = cursor.lastrowid
            
            # Add to recent contexts
            self.conn.execute('''
                INSERT INTO recent_contexts (user_id, interaction_id, relevance)
                VALUES (?, ?, ?)
            ''', (user_id, interaction_id, relevance))
        
        # If critical or high relevance, extract and store immediately
        if relevance >= Relevance.HIGH:
            self._extract_and_store_semantic_memory(user_id, interaction)

    def end_session(self, user_id: str) -> None:
        """
        End a conversation session, processing all context for long-term storage.
        """
        # Get all interactions for this user
        with self.conn:
            interaction_ids = self.conn.execute('''
                SELECT interaction_id FROM recent_contexts WHERE user_id = ?
            ''', (user_id,)).fetchall()
        
        interactions = []
        for (interaction_id,) in interaction_ids:
            data = self.conn.execute('''
                SELECT * FROM interactions WHERE id = ?
            ''', (interaction_id,)).fetchone()
            if data:
                interactions.append({
                    'timestamp': data[2],
                    'relevance': data[3],
                    'user_message': data[4],
                    'assistant_response': data[5],
                    'metadata': json.loads(data[6])
                })
        
        # Process interactions for semantic memories
        self._process_session_context(user_id, interactions)
        
        # Clean up SQLite
        with self.conn:
            self.conn.execute('DELETE FROM recent_contexts WHERE user_id = ?', (user_id,))
            self.conn.execute('DELETE FROM interactions WHERE id IN ({})'.format(
                ','.join('?' for _ in interaction_ids)
            ), [interaction_id for (interaction_id,) in interaction_ids])

    def _process_session_context(self, user_id: str, interactions: List[Dict]) -> None:
        """
        Process entire session context to extract important information.
        """
        # Sort by relevance
        interactions.sort(key=lambda x: x['relevance'], reverse=True)
        
        # Combine related interactions
        processed_memories = self._combine_related_interactions(interactions)
        
        # Store each processed memory
        for memory in processed_memories:
            confidence = min(1.0, memory['relevance'] + 0.2)  # Boost confidence a bit
            self.semantic_store.store_memory(
                content=memory['content'],
                category=memory['category'],
                metadata={
                    'source': 'session_context',
                    'timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'original_interactions': memory['source_indices']
                },
                confidence=confidence
            )

    def _combine_related_interactions(self, interactions: List[Dict]) -> List[Dict]:
        """
        Combine related interactions into coherent memories.
        """
        memories = []
        processed_indices = set()
        
        for i, interaction in enumerate(interactions):
            if i in processed_indices:
                continue
                
            # Skip low relevance interactions
            if interaction['relevance'] <= Relevance.LOW:
                continue
            
            related_indices = {i}
            combined_content = []
            
            # Find related interactions
            base_embedding = self.model.encode(
                f"{interaction['user_message']} {interaction['assistant_response']}"
            )
            
            for j, other in enumerate(interactions):
                if j != i and j not in processed_indices:
                    other_embedding = self.model.encode(
                        f"{other['user_message']} {other['assistant_response']}"
                    )
                    
                    similarity = np.dot(base_embedding, other_embedding) / (
                        np.linalg.norm(base_embedding) * np.linalg.norm(other_embedding)
                    )
                    
                    if similarity > 0.8:  # High similarity threshold
                        related_indices.add(j)
            
            # Combine related interactions
            for idx in related_indices:
                curr_interaction = interactions[idx]
                combined_content.append(
                    f"User: {curr_interaction['user_message']}\n"
                    f"Assistant: {curr_interaction['assistant_response']}"
                )
            
            # Create combined memory
            category = self._detect_category(combined_content)
            processed_indices.update(related_indices)
            
            memories.append({
                'content': "\n".join(combined_content),
                'category': category,
                'relevance': max(interactions[i]['relevance'] for i in related_indices),
                'source_indices': list(related_indices)
            })
        
        return memories

    def _detect_category(self, content_list: List[str]) -> str:
        """
        Detect the appropriate category for a memory based on content.
        """
        combined_text = " ".join(content_list).lower()
        
        category_patterns = {
            'preferences': [r'prefer', r'like', r'enjoy', r'rather', r'instead'],
            'personal': [r'name', r'age', r'live', r'family', r'job', r'work'],
            'health': [r'allerg', r'health', r'medical', r'condition', r'medication'],
            'skills': [r'can', r'know how', r'able to', r'experience', r'skilled'],
            'facts': [r'fact', r'true', r'always', r'never', r'must']
        }
        
        category_counts = Counter()
        
        for category, patterns in category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined_text):
                    category_counts[category] += 1
        
        if category_counts:
            return category_counts.most_common(1)[0][0]
        return 'general'

    def _extract_and_store_semantic_memory(self, user_id: str, interaction: Dict) -> None:
        """
        Extract and store important information from a single interaction.
        TODO: Run on separate thread
        """
        combined_content = (
            f"User: {interaction['user_message']}\n"
            f"Assistant: {interaction['assistant_response']}"
        )
        
        category = self._detect_category([combined_content])
        
        self.semantic_store.store_memory(
            content=combined_content,
            category=category,
            metadata={
                'source': 'direct_interaction',
                'timestamp': datetime.fromtimestamp(interaction['timestamp']).isoformat(),
                'user_id': user_id,
                'original_metadata': interaction['metadata']
            },
            confidence=interaction['relevance']
        )
        
# Example usage
# if __name__ == "__main__":
#     from semantic_memory import SemanticMemoryStore
    
#     # Initialize both memory systems
#     semantic_store = SemanticMemoryStore("long_term_memory.db")
#     memory_system = IntegratedMemorySystem(semantic_store)
    
#     # Simulate a conversation session
#     user_id = "user123"
    
#     # Add some interactions
#     memory_system.add_interaction(
#         user_id=user_id,
#         user_message="Hi there!",
#         assistant_response="Hello! How can I help you today?"
#     )
    
#     memory_system.add_interaction(
#         user_id=user_id,
#         user_message="Please remember that I'm allergic to peanuts",
#         assistant_response="I'll definitely remember your peanut allergy. This is important health information.",
#         metadata={"type": "health", "importance": "high"}
#     )
    
#     memory_system.add_interaction(
#         user_id=user_id,
#         user_message="I prefer to be called Alex instead of Alexander",
#         assistant_response="I'll remember to call you Alex.",
#         metadata={"type": "preference", "importance": "high"}
#     )