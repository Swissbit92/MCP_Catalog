"""RAG-based episodic memory for conversations.

This module provides semantic search over conversation history using FAISS
vector database and Ollama embeddings for local-first AI memory.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any
import logging
from datetime import datetime

try:
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain_community.vectorstores import FAISS
    import faiss
except ImportError as e:
    raise ImportError(
        "Required packages not installed. Run: pip install faiss-cpu langchain-community"
    ) from e

logger = logging.getLogger(__name__)


class EpisodicMemoryRAG:
    """Semantic search over conversation history using FAISS vector database.

    This class enables personas to find relevant past messages semantically,
    not just chronologically. Uses local Ollama embeddings for privacy.

    Features:
    - Local-first (no external API calls)
    - Semantic similarity search
    - Per-session vector stores
    - Automatic GPU detection (CPU fallback)
    """

    def __init__(self, embedding_model: Optional[str] = None):
        """Initialize the RAG memory system.

        Args:
            embedding_model: Ollama model for embeddings (default: from config)
        """
        from .config import get_embedding_model
        if embedding_model is None:
            embedding_model = get_embedding_model()
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.vectorstores: Dict[str, FAISS] = {}  # session_id -> FAISS instance
        self.use_gpu = faiss.get_num_gpus() > 0

        if self.use_gpu:
            logger.info(f"🚀 FAISS GPU acceleration enabled: {faiss.get_num_gpus()} device(s)")
        else:
            logger.info("⚙️ FAISS running on CPU (GPU not available)")

    def index_session(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        """Index all messages from a session for semantic search.

        Creates a FAISS vector store from conversation messages, enabling
        fast similarity search for relevant context retrieval.

        Args:
            session_id: Chat session ID
            messages: List of message dicts with keys: id, role, content, timestamp
        """
        if not messages:
            logger.warning(f"[RAG] No messages to index for session {session_id}")
            return

        # Format messages for indexing
        texts = []
        metadatas = []

        for i, msg in enumerate(messages):
            # Format: "user: message content" or "assistant: response content"
            text = f"{msg['role']}: {msg['content']}"
            metadata = {
                "session_id": session_id,
                "message_id": msg.get("id"),
                "role": msg["role"],
                "timestamp": msg.get("timestamp"),
                "index": i
            }
            texts.append(text)
            metadatas.append(metadata)

        # Create FAISS vector store
        try:
            vectorstore = FAISS.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas
            )

            # Move to GPU if available (10-50x speedup)
            if self.use_gpu:
                try:
                    gpu_resources = faiss.StandardGpuResources()
                    vectorstore.index = faiss.index_cpu_to_gpu(
                        gpu_resources,
                        0,  # GPU device ID
                        vectorstore.index
                    )
                    logger.info(f"✅ Session {session_id} FAISS index running on GPU")
                except Exception as e:
                    logger.warning(f"GPU transfer failed, using CPU: {e}")

            self.vectorstores[session_id] = vectorstore
            logger.info(f"[RAG] Indexed {len(texts)} messages for session {session_id}")

        except Exception as e:
            logger.error(f"[RAG] Failed to index session {session_id}: {e}")
            raise

    def search_memory(
        self,
        session_id: str,
        query: str,
        k: int = 10,
        min_relevance: float = 0.5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Search conversation memory semantically.

        Uses vector similarity to find relevant past messages, even if they
        don't share exact keywords with the query.

        Args:
            session_id: Chat session ID
            query: Search query (typically the user's current message)
            k: Number of results to return
            min_relevance: Minimum relevance score (0-1, lower = more strict)

        Returns:
            List of (message_dict, relevance_score) tuples, sorted by relevance
        """
        if session_id not in self.vectorstores:
            logger.warning(f"[RAG] Session {session_id} not indexed yet")
            return []

        vectorstore = self.vectorstores[session_id]

        try:
            # Perform similarity search
            results = vectorstore.similarity_search_with_score(
                query=query,
                k=k
            )

            # Filter by minimum relevance (FAISS returns distance, lower = more similar)
            # Convert distance to similarity score (invert and normalize)
            filtered_results = []
            for doc, distance in results:
                # Convert distance to similarity (assuming L2 distance)
                # Note: exact conversion depends on embedding space
                similarity = 1.0 / (1.0 + distance)

                if similarity >= min_relevance:
                    message_data = {
                        "role": doc.metadata["role"],
                        "content": doc.page_content.split(": ", 1)[1] if ": " in doc.page_content else doc.page_content,
                        "timestamp": doc.metadata.get("timestamp"),
                        "index": doc.metadata["index"],
                        "message_id": doc.metadata.get("message_id")
                    }
                    filtered_results.append((message_data, similarity))

            logger.info(
                f"[RAG] Found {len(filtered_results)}/{len(results)} relevant memories "
                f"for query: '{query[:50]}...'"
            )

            return filtered_results

        except Exception as e:
            logger.error(f"[RAG] Search failed for session {session_id}: {e}")
            return []

    def get_relevant_context(
        self,
        session_id: str,
        query: str,
        max_messages: int = 10
    ) -> List[Dict[str, Any]]:
        """Get relevant conversation context for a query.

        Retrieves semantically relevant past messages and sorts them
        chronologically for natural context flow.

        Args:
            session_id: Chat session ID
            query: Current user query
            max_messages: Maximum messages to retrieve

        Returns:
            List of relevant message dicts (sorted chronologically)
        """
        results = self.search_memory(session_id, query, k=max_messages)

        if not results:
            return []

        # Extract messages and sort by conversation order (chronological)
        messages = []
        for message_data, relevance in results:
            message_data["relevance"] = relevance
            messages.append(message_data)

        # Sort by index (chronological order)
        messages.sort(key=lambda x: x["index"])

        logger.debug(
            f"[RAG] Retrieved {len(messages)} relevant messages "
            f"(relevance range: {min(m['relevance'] for m in messages):.2f}-"
            f"{max(m['relevance'] for m in messages):.2f})"
        )

        return messages

    def update_session(
        self,
        session_id: str,
        new_messages: List[Dict[str, Any]],
        full_history: List[Dict[str, Any]]
    ) -> None:
        """Update vector store with new messages.

        Efficiently updates the index when new messages are added to a session.
        Currently rebuilds the entire index (simple approach).

        Args:
            session_id: Chat session ID
            new_messages: Newly added messages
            full_history: Complete conversation history including new messages
        """
        # Simple approach: rebuild index with full history
        # TODO: Implement incremental update for better performance
        logger.debug(f"[RAG] Updating session {session_id} with {len(new_messages)} new messages")
        self.index_session(session_id, full_history)

    def clear_session(self, session_id: str) -> None:
        """Clear vector store for a session.

        Removes the FAISS index to free memory when a session is deleted.

        Args:
            session_id: Chat session ID to clear
        """
        if session_id in self.vectorstores:
            del self.vectorstores[session_id]
            logger.info(f"[RAG] Cleared vector store for session {session_id}")

    def get_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about indexed sessions.

        Args:
            session_id: Specific session (or None for all sessions)

        Returns:
            Dictionary with indexing statistics
        """
        if session_id:
            if session_id not in self.vectorstores:
                return {"error": f"Session {session_id} not indexed"}

            vectorstore = self.vectorstores[session_id]
            return {
                "session_id": session_id,
                "indexed_messages": vectorstore.index.ntotal,
                "using_gpu": self.use_gpu
            }
        else:
            return {
                "total_sessions": len(self.vectorstores),
                "sessions": list(self.vectorstores.keys()),
                "using_gpu": self.use_gpu,
                "total_indexed_messages": sum(
                    vs.index.ntotal for vs in self.vectorstores.values()
                )
            }
