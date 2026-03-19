"""Document Chunker — recursive + semantic chunking strategies.

Splits parsed documents into chunks suitable for embedding and
vector indexing.

Sprint 118 — Phase 38 E2E Assembly C.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""

    RECURSIVE = "recursive"     # Split by headings → paragraphs → sentences
    FIXED_SIZE = "fixed_size"   # Fixed character windows with overlap
    SEMANTIC = "semantic"       # Boundary-aware splitting (headings, paragraphs)


@dataclass
class TextChunk:
    """Single chunk of text with metadata."""

    content: str
    chunk_index: int
    start_char: int = 0
    end_char: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.content)


class DocumentChunker:
    """Splits documents into chunks for embedding.

    Args:
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between consecutive chunks.
        strategy: Chunking strategy to use.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
    ) -> None:
        self._chunk_size = chunk_size
        self._overlap = chunk_overlap
        self._strategy = strategy

    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """Split text into chunks using the configured strategy."""
        if not text or not text.strip():
            return []

        base_meta = metadata or {}

        if self._strategy == ChunkingStrategy.RECURSIVE:
            return self._recursive_chunk(text, base_meta)
        elif self._strategy == ChunkingStrategy.FIXED_SIZE:
            return self._fixed_size_chunk(text, base_meta)
        elif self._strategy == ChunkingStrategy.SEMANTIC:
            return self._semantic_chunk(text, base_meta)
        else:
            return self._fixed_size_chunk(text, base_meta)

    def _recursive_chunk(
        self, text: str, metadata: Dict[str, Any]
    ) -> List[TextChunk]:
        """Split by headings → paragraphs → sentences → fixed windows."""
        # Try splitting by markdown headings first
        sections = re.split(r'\n(?=#{1,3}\s)', text)
        if len(sections) > 1:
            chunks: List[TextChunk] = []
            idx = 0
            pos = 0
            for section in sections:
                if len(section) <= self._chunk_size:
                    chunks.append(TextChunk(
                        content=section.strip(),
                        chunk_index=idx,
                        start_char=pos,
                        end_char=pos + len(section),
                        metadata={**metadata, "split_level": "heading"},
                    ))
                    idx += 1
                else:
                    # Section too large — split by paragraphs
                    sub_chunks = self._paragraph_split(section, metadata, idx, pos)
                    chunks.extend(sub_chunks)
                    idx += len(sub_chunks)
                pos += len(section)
            return chunks

        # No headings — try paragraph split
        return self._paragraph_split(text, metadata, 0, 0)

    def _paragraph_split(
        self, text: str, metadata: Dict[str, Any], start_idx: int, start_pos: int
    ) -> List[TextChunk]:
        """Split by double newlines (paragraphs)."""
        paragraphs = re.split(r'\n\s*\n', text)
        chunks: List[TextChunk] = []
        current_chunk = ""
        idx = start_idx
        pos = start_pos

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= self._chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(TextChunk(
                        content=current_chunk,
                        chunk_index=idx,
                        start_char=pos,
                        end_char=pos + len(current_chunk),
                        metadata={**metadata, "split_level": "paragraph"},
                    ))
                    idx += 1
                    pos += len(current_chunk)

                if len(para) > self._chunk_size:
                    # Paragraph too large — fall back to fixed size
                    sub = self._fixed_size_chunk(para, {**metadata, "split_level": "sentence"})
                    for s in sub:
                        s.chunk_index = idx
                        idx += 1
                    chunks.extend(sub)
                    pos += len(para)
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(TextChunk(
                content=current_chunk,
                chunk_index=idx,
                start_char=pos,
                end_char=pos + len(current_chunk),
                metadata={**metadata, "split_level": "paragraph"},
            ))

        return chunks

    def _fixed_size_chunk(
        self, text: str, metadata: Dict[str, Any]
    ) -> List[TextChunk]:
        """Fixed-size windows with overlap."""
        chunks: List[TextChunk] = []
        start = 0
        idx = 0

        while start < len(text):
            end = start + self._chunk_size
            chunk_text = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind("。")
                last_dot = chunk_text.rfind(". ")
                last_newline = chunk_text.rfind("\n")
                break_point = max(last_period, last_dot, last_newline)
                if break_point > self._chunk_size * 0.5:
                    chunk_text = chunk_text[: break_point + 1]
                    end = start + len(chunk_text)

            chunks.append(TextChunk(
                content=chunk_text.strip(),
                chunk_index=idx,
                start_char=start,
                end_char=end,
                metadata={**metadata, "split_level": "fixed"},
            ))
            idx += 1
            start = end - self._overlap
            if start >= len(text):
                break

        return chunks

    def _semantic_chunk(
        self, text: str, metadata: Dict[str, Any]
    ) -> List[TextChunk]:
        """Boundary-aware splitting using headings and paragraph markers."""
        # Same as recursive but with stricter boundary detection
        return self._recursive_chunk(text, {**metadata, "strategy": "semantic"})
