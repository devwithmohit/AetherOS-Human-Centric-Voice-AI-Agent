"""LLM client wrapper for llama-cpp-python."""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from llama_cpp import Llama


class LLMClient:
    """Wrapper for llama-cpp-python with model management.

    Supports CPU-only inference with quantized models (GGUF format).
    Recommended models:
    - Mistral-7B-Instruct-v0.2 (Q4_K_M.gguf) - ~4GB
    - Llama-2-7B-Chat (Q4_K_M.gguf) - ~4GB
    - TinyLlama-1.1B (Q4_K_M.gguf) - ~700MB for testing
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 4096,
        n_threads: int = 4,
        n_gpu_layers: int = 0,  # CPU-only
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 0.9,
        verbose: bool = False,
    ):
        """Initialize LLM client.

        Args:
            model_path: Path to GGUF model file. If None, uses MODEL_PATH env var.
            n_ctx: Context window size (tokens)
            n_threads: CPU threads to use
            n_gpu_layers: GPU layers (0 for CPU-only)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            verbose: Enable verbose logging
        """
        # Get model path from env or parameter
        if model_path is None:
            model_path = os.getenv("MODEL_PATH", "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")

        self.model_path = Path(model_path)
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p

        # Lazy load model
        self._llm: Optional[Llama] = None
        self.verbose = verbose

        if not self.model_path.exists():
            print(f"⚠️  Model not found: {self.model_path}")
            print(f"   Download a GGUF model to: {self.model_path}")
            print(f"   Example: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF")

    def _load_model(self):
        """Lazy load the LLM model."""
        if self._llm is None:
            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Model not found: {self.model_path}\n"
                    f"Download a GGUF model from HuggingFace.\n"
                    f"Example: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
                )

            print(f"Loading model: {self.model_path.name}...")
            self._llm = Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=0,  # CPU-only
                verbose=self.verbose,
            )
            print(f"✓ Model loaded ({self.n_ctx} context tokens)")

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt text
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop: Stop sequences (e.g., ["\n\n", "Observation:"])

        Returns:
            Generated text string
        """
        self._load_model()

        if stop is None:
            stop = []

        output = self._llm(
            prompt,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature or self.temperature,
            top_p=self.top_p,
            stop=stop,
            echo=False,
        )

        return output["choices"][0]["text"].strip()

    def generate_with_metadata(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate text with full metadata.

        Args:
            prompt: Input prompt text
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop: Stop sequences

        Returns:
            Dictionary with 'text', 'tokens', 'logprobs', etc.
        """
        self._load_model()

        if stop is None:
            stop = []

        output = self._llm(
            prompt,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature or self.temperature,
            top_p=self.top_p,
            stop=stop,
            echo=False,
        )

        choice = output["choices"][0]
        return {
            "text": choice["text"].strip(),
            "tokens": output["usage"]["completion_tokens"],
            "finish_reason": choice["finish_reason"],
        }

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Input text

        Returns:
            Number of tokens
        """
        self._load_model()
        return len(self._llm.tokenize(text.encode("utf-8")))

    def get_context_size(self) -> int:
        """Get model context window size.

        Returns:
            Context size in tokens
        """
        return self.n_ctx

    def is_loaded(self) -> bool:
        """Check if model is loaded.

        Returns:
            True if model is loaded in memory
        """
        return self._llm is not None

    def unload(self):
        """Unload model from memory."""
        if self._llm is not None:
            del self._llm
            self._llm = None
            print("Model unloaded")
