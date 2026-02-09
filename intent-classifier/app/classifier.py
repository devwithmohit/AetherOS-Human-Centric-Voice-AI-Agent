"""Hybrid intent classifier combining regex and ML approaches."""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
import numpy as np

from .intents import IntentType
from .patterns import match_pattern, ALL_PATTERNS
from .entities import EntityExtractor


@dataclass
class IntentResult:
    """Result of intent classification.

    Attributes:
        intent: The classified IntentType
        confidence: Confidence score (0.0 to 1.0)
        entities: Extracted entities from the text
        method: Classification method used ('regex', 'semantic', 'llm')
        latency_ms: Time taken for classification in milliseconds
        raw_text: Original input text
    """

    intent: IntentType
    confidence: float
    entities: Dict[str, Any]
    method: str
    latency_ms: float
    raw_text: str


class HybridIntentClassifier:
    """Hybrid intent classifier using regex patterns and semantic similarity.

    Classification strategy:
    1. Try regex pattern matching (fast, deterministic)
    2. If no match or low confidence, use sentence-transformers (semantic)
    3. If still low confidence, can fallback to LLM (optional)

    Attributes:
        model: SentenceTransformer model for semantic similarity
        entity_extractor: EntityExtractor for extracting entities
        semantic_threshold: Minimum confidence for semantic matching
        intent_embeddings: Pre-computed embeddings for each intent
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        semantic_threshold: float = 0.6,
        use_gpu: bool = False,
    ):
        """Initialize the hybrid classifier.

        Args:
            model_name: Name of sentence-transformers model to use
            semantic_threshold: Minimum confidence for semantic classification
            use_gpu: Whether to use GPU acceleration (if available)
        """
        self.semantic_threshold = semantic_threshold
        self.entity_extractor = EntityExtractor()

        # Load semantic model (lazy loading in production)
        self.model: Optional[SentenceTransformer] = None
        self.model_name = model_name
        self.use_gpu = use_gpu

        # Intent example embeddings (computed on first use)
        self.intent_embeddings: Optional[Dict[IntentType, np.ndarray]] = None
        self.intent_examples: Dict[IntentType, List[str]] = self._get_intent_examples()

    def _load_model(self):
        """Lazy load the semantic model."""
        if self.model is None:
            device = "cuda" if self.use_gpu else "cpu"
            self.model = SentenceTransformer(self.model_name, device=device)
            self._compute_intent_embeddings()

    def _get_intent_examples(self) -> Dict[IntentType, List[str]]:
        """Get example utterances for each intent type.

        Returns:
            Dictionary mapping IntentType to example utterances
        """
        # TODO: Load from training data file (intent-classifier/data/intent_examples.json)
        # For now, return basic examples
        return {
            IntentType.OPEN_APP: ["open chrome", "launch spotify", "start vscode"],
            IntentType.CLOSE_APP: ["close chrome", "quit spotify", "exit vscode"],
            IntentType.GET_WEATHER: ["what's the weather", "how's the weather today"],
            IntentType.GET_TIME: ["what time is it", "current time"],
            IntentType.PLAY_MUSIC: ["play music", "play some songs"],
            IntentType.SET_TIMER: ["set a timer for 5 minutes", "timer 10 seconds"],
            IntentType.SEARCH_WEB: ["search for python tutorials", "google machine learning"],
            IntentType.HELP: ["help", "what can you do"],
            # Add more examples as needed
        }

    def _compute_intent_embeddings(self):
        """Pre-compute embeddings for intent examples."""
        if self.model is None:
            return

        self.intent_embeddings = {}

        for intent, examples in self.intent_examples.items():
            # Average embeddings of all examples for this intent
            embeddings = self.model.encode(examples, convert_to_numpy=True)
            avg_embedding = np.mean(embeddings, axis=0)
            self.intent_embeddings[intent] = avg_embedding

    def classify(self, text: str) -> IntentResult:
        """Classify user input text to an intent.

        Args:
            text: User input text

        Returns:
            IntentResult with classification details
        """
        start_time = time.time()

        # Normalize input
        text = text.strip()

        if not text:
            return self._create_result(
                IntentType.UNKNOWN,
                0.0,
                {},
                "empty",
                time.time() - start_time,
                text,
            )

        # Step 1: Try regex pattern matching
        pattern_result = match_pattern(text)

        if pattern_result:
            intent = pattern_result["intent"]
            entities = self.entity_extractor.extract(text, intent.value)

            latency = (time.time() - start_time) * 1000
            return self._create_result(
                intent,
                0.95,  # High confidence for regex matches
                entities,
                "regex",
                latency,
                text,
            )

        # Step 2: Try semantic similarity
        semantic_result = self._classify_semantic(text)

        if semantic_result and semantic_result["confidence"] >= self.semantic_threshold:
            intent = semantic_result["intent"]
            entities = self.entity_extractor.extract(text, intent.value)

            latency = (time.time() - start_time) * 1000
            return self._create_result(
                intent,
                semantic_result["confidence"],
                entities,
                "semantic",
                latency,
                text,
            )

        # Step 3: Fallback to UNKNOWN
        latency = (time.time() - start_time) * 1000
        return self._create_result(
            IntentType.UNKNOWN,
            0.0,
            {},
            "fallback",
            latency,
            text,
        )

    def _classify_semantic(self, text: str) -> Optional[Dict[str, Any]]:
        """Classify using semantic similarity.

        Args:
            text: Input text

        Returns:
            Dict with 'intent' and 'confidence' if successful, None otherwise
        """
        # Lazy load model
        if self.model is None:
            self._load_model()

        if self.intent_embeddings is None or len(self.intent_embeddings) == 0:
            return None

        # Encode input text
        text_embedding = self.model.encode([text], convert_to_numpy=True)[0]

        # Compute cosine similarity with each intent
        best_intent = None
        best_similarity = -1.0

        for intent, intent_embedding in self.intent_embeddings.items():
            # Cosine similarity
            similarity = np.dot(text_embedding, intent_embedding) / (
                np.linalg.norm(text_embedding) * np.linalg.norm(intent_embedding)
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_intent = intent

        if best_intent and best_similarity > 0:
            return {
                "intent": best_intent,
                "confidence": float(best_similarity),
            }

        return None

    def _create_result(
        self,
        intent: IntentType,
        confidence: float,
        entities: Dict[str, Any],
        method: str,
        latency: float,
        raw_text: str,
    ) -> IntentResult:
        """Create an IntentResult object.

        Args:
            intent: Classified intent
            confidence: Confidence score
            entities: Extracted entities
            method: Classification method
            latency: Latency in seconds
            raw_text: Original input text

        Returns:
            IntentResult object
        """
        latency_ms = latency * 1000 if latency < 10 else latency  # Handle seconds vs ms

        return IntentResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
            method=method,
            latency_ms=latency_ms,
            raw_text=raw_text,
        )

    def batch_classify(self, texts: List[str]) -> List[IntentResult]:
        """Classify multiple texts in batch.

        Args:
            texts: List of input texts

        Returns:
            List of IntentResult objects
        """
        return [self.classify(text) for text in texts]

    def add_intent_examples(self, intent: IntentType, examples: List[str]):
        """Add training examples for an intent.

        Args:
            intent: The IntentType to add examples for
            examples: List of example utterances
        """
        if intent not in self.intent_examples:
            self.intent_examples[intent] = []

        self.intent_examples[intent].extend(examples)

        # Recompute embeddings if model is loaded
        if self.model is not None:
            self._compute_intent_embeddings()

    def get_stats(self) -> Dict[str, Any]:
        """Get classifier statistics.

        Returns:
            Dictionary with classifier statistics
        """
        return {
            "model_name": self.model_name,
            "model_loaded": self.model is not None,
            "num_intents": len(self.intent_examples),
            "total_examples": sum(len(ex) for ex in self.intent_examples.values()),
            "semantic_threshold": self.semantic_threshold,
            "pattern_count": len(ALL_PATTERNS),
        }
