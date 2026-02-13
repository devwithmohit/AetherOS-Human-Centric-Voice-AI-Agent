"""Episodic memory store using ChromaDB."""

from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings

logger = logging.getLogger(__name__)


class EpisodicMemory:
    """ChromaDB-based episodic memory for semantic search."""

    def __init__(self) -> None:
        """Initialize ChromaDB client."""
        self.client: Optional[chromadb.Client] = None
        self.collection_name = "episodic_memories"

    async def connect(self) -> None:
        """Establish ChromaDB connection."""
        try:
            # Use modern ChromaDB PersistentClient API
            self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

            # Get or create collection
            self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Episodic memories with semantic embeddings"},
            )

            logger.info("Connected to ChromaDB successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to ChromaDB: {e}. Running without episodic memory.")
            self.client = None  # Run without ChromaDB

    async def disconnect(self) -> None:
        """Close ChromaDB connection."""
        if self.client:
            # ChromaDB auto-persists
            logger.info("ChromaDB session ended")

    async def store_episode(
        self,
        user_id: str,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        episode_id: Optional[str] = None,
    ) -> str:
        """Store an episodic memory.

        Args:
            user_id: User identifier
            session_id: Session identifier
            content: Episode content (will be embedded)
            metadata: Additional metadata
            episode_id: Optional custom ID (auto-generated if None)

        Returns:
            Episode ID
        """
        if not self.client:
            raise RuntimeError("ChromaDB not connected")

        try:
            collection = self.client.get_collection(self.collection_name)

            # Generate ID if not provided
            if episode_id is None:
                episode_id = f"{user_id}:{session_id}:{datetime.utcnow().isoformat()}"

            # Prepare metadata
            episode_metadata = {
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {}),
            }

            # Store with automatic embedding
            collection.add(
                ids=[episode_id],
                documents=[content],
                metadatas=[episode_metadata],
            )

            logger.debug(f"Stored episode {episode_id}")
            return episode_id
        except Exception as e:
            logger.error(f"Failed to store episode: {e}")
            raise

    async def query_episodes(
        self,
        user_id: str,
        query_text: str,
        n_results: int = 10,
        session_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query episodic memories using semantic search.

        Args:
            user_id: User identifier
            query_text: Search query
            n_results: Number of results to return
            session_id: Optional session filter
            filters: Additional metadata filters

        Returns:
            List of matching episodes with scores
        """
        if not self.client:
            raise RuntimeError("ChromaDB not connected")

        try:
            collection = self.client.get_collection(self.collection_name)

            # Build where filter
            where_filter: Dict[str, Any] = {"user_id": user_id}

            if session_id:
                where_filter["session_id"] = session_id

            if filters:
                where_filter.update(filters)

            # Query with semantic search
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter,
            )

            # Format results
            episodes = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    episodes.append(
                        {
                            "id": results["ids"][0][i],
                            "content": results["documents"][0][i] if results["documents"] else None,
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                            "distance": results["distances"][0][i]
                            if results["distances"]
                            else None,
                        }
                    )

            logger.debug(f"Query returned {len(episodes)} episodes")
            return episodes
        except Exception as e:
            logger.error(f"Failed to query episodes: {e}")
            return []

    async def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve specific episode by ID.

        Args:
            episode_id: Episode identifier

        Returns:
            Episode data or None
        """
        if not self.client:
            raise RuntimeError("ChromaDB not connected")

        try:
            collection = self.client.get_collection(self.collection_name)

            result = collection.get(
                ids=[episode_id],
                include=["documents", "metadatas"],
            )

            if not result["ids"]:
                return None

            return {
                "id": result["ids"][0],
                "content": result["documents"][0] if result["documents"] else None,
                "metadata": result["metadatas"][0] if result["metadatas"] else {},
            }
        except Exception as e:
            logger.error(f"Failed to get episode {episode_id}: {e}")
            return None

    async def delete_episode(self, episode_id: str) -> bool:
        """Delete specific episode.

        Args:
            episode_id: Episode identifier

        Returns:
            True if deleted, False otherwise
        """
        if not self.client:
            raise RuntimeError("ChromaDB not connected")

        try:
            collection = self.client.get_collection(self.collection_name)
            collection.delete(ids=[episode_id])
            logger.debug(f"Deleted episode {episode_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete episode {episode_id}: {e}")
            return False

    async def delete_user_episodes(self, user_id: str, session_id: Optional[str] = None) -> int:
        """Delete all episodes for a user or session.

        Args:
            user_id: User identifier
            session_id: Optional session filter

        Returns:
            Number of episodes deleted
        """
        if not self.client:
            raise RuntimeError("ChromaDB not connected")

        try:
            collection = self.client.get_collection(self.collection_name)

            # Build where filter
            where_filter: Dict[str, Any] = {"user_id": user_id}
            if session_id:
                where_filter["session_id"] = session_id

            # Get matching IDs
            result = collection.get(
                where=where_filter,
                include=[],
            )

            if result["ids"]:
                collection.delete(ids=result["ids"])
                count = len(result["ids"])
                logger.info(f"Deleted {count} episodes for user {user_id}")
                return count

            return 0
        except Exception as e:
            logger.error(f"Failed to delete user episodes: {e}")
            return 0

    async def get_recent_episodes(
        self,
        user_id: str,
        limit: int = 100,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent episodes (chronological order).

        Args:
            user_id: User identifier
            limit: Maximum number of episodes
            session_id: Optional session filter

        Returns:
            List of recent episodes
        """
        if not self.client:
            raise RuntimeError("ChromaDB not connected")

        try:
            collection = self.client.get_collection(self.collection_name)

            where_filter: Dict[str, Any] = {"user_id": user_id}
            if session_id:
                where_filter["session_id"] = session_id

            result = collection.get(
                where=where_filter,
                limit=limit,
                include=["documents", "metadatas"],
            )

            episodes = []
            if result["ids"]:
                for i in range(len(result["ids"])):
                    episodes.append(
                        {
                            "id": result["ids"][i],
                            "content": result["documents"][i] if result["documents"] else None,
                            "metadata": result["metadatas"][i] if result["metadatas"] else {},
                        }
                    )

            # Sort by timestamp (newest first)
            episodes.sort(
                key=lambda x: x["metadata"].get("timestamp", ""),
                reverse=True,
            )

            return episodes
        except Exception as e:
            logger.error(f"Failed to get recent episodes: {e}")
            return []

    async def count_episodes(self, user_id: str, session_id: Optional[str] = None) -> int:
        """Count episodes for a user or session.

        Args:
            user_id: User identifier
            session_id: Optional session filter

        Returns:
            Number of episodes
        """
        if not self.client:
            raise RuntimeError("ChromaDB not connected")

        try:
            collection = self.client.get_collection(self.collection_name)

            where_filter: Dict[str, Any] = {"user_id": user_id}
            if session_id:
                where_filter["session_id"] = session_id

            result = collection.get(
                where=where_filter,
                include=[],
            )

            return len(result["ids"]) if result["ids"] else 0
        except Exception as e:
            logger.error(f"Failed to count episodes: {e}")
            return 0


# Global instance
episodic_memory = EpisodicMemory()
