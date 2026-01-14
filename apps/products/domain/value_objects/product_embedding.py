"""
Product embedding value object for vector search.
"""
from dataclasses import dataclass
from typing import List

from shared.domain import ValueObject


@dataclass(frozen=True)
class ProductEmbedding(ValueObject):
    """Product embedding vector for semantic search."""
    vector: List[float]

    def __post_init__(self):
        if len(self.vector) != 1536:  # OpenAI ada-002 dimensions
            raise ValueError(f"Embedding must have 1536 dimensions, got {len(self.vector)}")

    @property
    def dimensions(self) -> int:
        """Get the number of dimensions."""
        return len(self.vector)
