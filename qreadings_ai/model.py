"""Model adapter layer for QREADINGS.

The core engine remains model-agnostic.  A local GGUF model can be connected
through llama-cpp-python without making that package a hard dependency of the
core architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ModelAdapter(Protocol):
    """Minimal interface required by the cognitive engine."""

    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        ...


@dataclass
class MockModel:
    """Deterministic adapter useful for tests and architecture development."""

    response: str = "{}"

    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        del prompt, max_tokens
        return self.response


class LlamaCppModel:
    """Optional local GGUF adapter using llama-cpp-python.

    Importing this class does not require llama-cpp-python until an instance is
    constructed, keeping the base package dependency-free.
    """

    def __init__(
        self,
        model_path: str,
        *,
        n_ctx: int = 2048,
        n_threads: int | None = None,
        n_batch: int = 128,
        n_gpu_layers: int = 0,
        **kwargs: Any,
    ) -> None:
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise RuntimeError(
                "llama-cpp-python is required for LlamaCppModel. "
                "Install the optional local-model dependency first."
            ) from exc

        options: dict[str, Any] = {
            "model_path": model_path,
            "n_ctx": n_ctx,
            "n_batch": n_batch,
            "n_gpu_layers": n_gpu_layers,
            "verbose": False,
        }
        if n_threads is not None:
            options["n_threads"] = n_threads
        options.update(kwargs)
        self._llama = Llama(**options)

    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        result = self._llama(
            prompt,
            max_tokens=max_tokens,
            temperature=0.1,
            top_p=0.9,
        )
        return str(result["choices"][0]["text"])
