from typing import List, Dict, Optional, Any, Set
import redis
import json
from datetime import datetime, timedelta
import time
from dataclasses import dataclass
import numpy as np
from sentence_transformers import SentenceTransformer
import re
from collections import Counter

@dataclass
class Relevance:
    CRITICAL = 1.0    # Must keep (user preferences, corrections)
    HIGH = 0.8       # Very relevant (key questions, important statements)
    MEDIUM = 0.5     # Moderately relevant (context, clarifications)
    LOW = 0.2        # Might be relevant (casual statements)
    IGNORE = 0.0     # Don't store (greetings, acknowledgments)

class IntegratedMemorySystem:
    def __init__(self, 
                 semantic_store: 'SemanticMemoryStore',
                 redis_host='localhost', 
                 redis_port=6379, 
                 redis_db=0,
                 context_ttl: int = 24*60*60):  # 24 hours
        """
        Initialize both memory systems.
        
        Args:
            semantic_store: Instance of SemanticMemoryStore for long-term memory
            redis_host: Redis host for short-term memory
            redis_port: Redis port
            redis_db: Redis database number
            context_ttl: Time to live for Redis entries in seconds
        """
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.semantic_store = semantic_store
        self.context_ttl = context_ttl
        # Load model for importance detection
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def _get_user_key(self, user_id: str, key_type: str) -> str:
        """Generate Redis key for different types of user data."""
        return f"user:{user_id}:{key_type}"

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
            relevance = self._detect_relevance(user_message, assistant_response)
            
        timestamp = time.time()
        interaction = {
            'timestamp': timestamp,
            'relevance': relevance,
            'user_message': user_message,
            'assistant_response': assistant_response,
            'metadata': metadata or {}
        }
        
        # Store in Redis
        interaction_key = f"interaction:{timestamp}"
        full_key = self._get_user_key(user_id, interaction_key)
        
        pipeline = self.redis.pipeline()
        
        # Store full interaction
        pipeline.setex(
            full_key,
            self.context_ttl,
            json.dumps(interaction)
        )
        
        # Add to sorted set for relevance tracking
        context_key = self._get_user_key(user_id, "recent_contexts")
        pipeline.zadd(context_key, {full_key: relevance})
        pipeline.expire(context_key, self.context_ttl)
        
        # If critical or high relevance, extract and store immediately
        if relevance >= Relevance.HIGH:
            self._extract_and_store_semantic_memory(user_id, interaction)
            
        pipeline.execute()

    def _detect_relevance(self, user_message: str, assistant_response: str) -> float:
        """
        Automatically detect relevance of an interaction.
        Uses heuristics and embeddings to determine importance.
        """
        combined_text = f"{user_message} {assistant_response}"
        
        # Check for high-importance indicators
        critical_patterns = [
            r"(?i)remember this",
            r"(?i)important",
            r"(?i)don't forget",
            r"(?i)always",
            r"(?i)never",
            r"(?i)must",
            r"(?i)prefer",
            r"(?i)allerg",
            r"(?i)call me",
            r"(?i)my name"
        ]
        
        for pattern in critical_patterns:
            if re.search(pattern, combined_text):
                return Relevance.CRITICAL
        
        # Check for low-importance indicators
        ignore_patterns = [
            r"(?i)^hi$",
            r"(?i)^hello$",
            r"(?i)^thanks?$",
            r"(?i)^okay$",
            r"(?i)^bye$"
        ]
        
        for pattern in ignore_patterns:
            if re.search(pattern, combined_text):
                return Relevance.IGNORE
        
        # Use embedding similarity to known important topics
        # This could be expanded based on your specific needs
        important_topics = [
            "preference", "fact", "information", "detail",
            "remember", "important", "specific", "personal"
        ]
        
        text_embedding = self.model.encode(combined_text)
        topic_embeddings = self.model.encode(important_topics)
        
        # Calculate max similarity to important topics
        similarities = np.dot(topic_embeddings, text_embedding) / (
            np.linalg.norm(topic_embeddings, axis=1) * np.linalg.norm(text_embedding)
        )
        max_similarity = float(np.max(similarities))
        
        # Convert similarity to relevance score
        if max_similarity > 0.8:
            return Relevance.HIGH
        elif max_similarity > 0.6:
            return Relevance.MEDIUM
        else:
            return Relevance.LOW

    def end_session(self, user_id: str) -> None:
        """
        End a conversation session, processing all context for long-term storage.
        """
        # Get all interactions for this user
        context_key = self._get_user_key(user_id, "recent_contexts")
        interaction_keys = self.redis.zrange(context_key, 0, -1)
        
        interactions = []
        for key in interaction_keys:
            data = self.redis.get(key)
            if data:
                interactions.append(json.loads(data))
        
        # Process interactions for semantic memories
        self._process_session_context(user_id, interactions)
        
        # Clean up Redis
        pipeline = self.redis.pipeline()
        for key in interaction_keys:
            pipeline.delete(key)
        pipeline.delete(context_key)
        pipeline.execute()

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