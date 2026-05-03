"""Article-based legal document chunker with fallback character-based chunking."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Chunk:
    chunk_id: str
    source: str
    text: str
    chapter: str = ""
    section: str = ""
    article: str = ""
    char_start: int = 0
    char_end: int = 0

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "text": self.text,
            "chapter": self.chapter,
            "section": self.section,
            "article": self.article,
            "char_start": self.char_start,
            "char_end": self.char_end,
        }


# Patterns ordered from most specific to least specific
_CHAPTER_RE = re.compile(
    r"(?:CHAPTER|Chapter|TITRE|Titre|ABSCHNITT|Bölüm|BÖLÜM)\s+([IVXivx\d]+[.\-]?\s*[\w\s]*)",
    re.MULTILINE,
)
_SECTION_RE = re.compile(
    r"(?:SECTION|Section|SOUS-TITRE|Unterabschnitt|MADDE GRUBU)\s+([\d.]+\s*[\w\s]*)",
    re.MULTILINE,
)
_ARTICLE_RE = re.compile(
    r"(?:Article|ARTICLE|Art\.|ART\.|§|Madde|MADDE|Section|Sec\.)\s*([\d.]+[a-zA-Z]?)",
    re.MULTILINE,
)

_MIN_ARTICLES_FOR_ARTICLE_MODE = 3
_MIN_COVERAGE_RATIO = 0.25  # at least 25% of text must be within detected articles

_CHAR_CHUNK_SIZE = 650
_CHAR_OVERLAP = 90
_SPLIT_RE = re.compile(r"(?<=[.!?;])\s+")


class ArticleChunker:
    def chunk(self, text: str, source: str) -> List[Chunk]:
        chunks = self._article_chunk(text, source)
        if chunks:
            return chunks
        return self._char_chunk(text, source)

    # ── Article-based ──────────────────────────────────────────────────────────

    def _article_chunk(self, text: str, source: str) -> List[Chunk]:
        matches = list(_ARTICLE_RE.finditer(text))
        if len(matches) < _MIN_ARTICLES_FOR_ARTICLE_MODE:
            return []

        # Check coverage: fraction of characters within article spans
        total_chars = len(text)
        covered = 0
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else total_chars
            covered += end - start
        if covered / total_chars < _MIN_COVERAGE_RATIO:
            return []

        chunks: List[Chunk] = []
        current_chapter = ""
        current_section = ""

        for i, m in enumerate(matches):
            article_label = m.group(0).strip()
            art_start = m.start()
            art_end = matches[i + 1].start() if i + 1 < len(matches) else total_chars

            # Update running hierarchy from the preceding text
            preceding = text[max(0, art_start - 500) : art_start]
            chapter_m = _CHAPTER_RE.search(preceding)
            if chapter_m:
                current_chapter = chapter_m.group(0).strip()
            section_m = _SECTION_RE.search(preceding)
            if section_m:
                current_section = section_m.group(0).strip()

            chunk_text = text[art_start:art_end].strip()
            if not chunk_text:
                continue

            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    source=source,
                    text=chunk_text,
                    chapter=current_chapter,
                    section=current_section,
                    article=article_label,
                    char_start=art_start,
                    char_end=art_end,
                )
            )

        return chunks

    # ── Character-based fallback ───────────────────────────────────────────────

    def _char_chunk(self, text: str, source: str) -> List[Chunk]:
        # Split on sentence boundaries first
        sentences = _SPLIT_RE.split(text)
        chunks: List[Chunk] = []
        current: List[str] = []
        current_len = 0
        pos = 0

        for sent in sentences:
            if current_len + len(sent) > _CHAR_CHUNK_SIZE and current:
                chunk_text = " ".join(current)
                start = text.find(chunk_text[:50], pos)
                end = start + len(chunk_text)
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid.uuid4()),
                        source=source,
                        text=chunk_text,
                        char_start=max(0, start),
                        char_end=min(len(text), end),
                    )
                )
                # Overlap: keep last sentence(s) totalling ~_CHAR_OVERLAP chars
                overlap: List[str] = []
                overlap_len = 0
                for s in reversed(current):
                    if overlap_len + len(s) > _CHAR_OVERLAP:
                        break
                    overlap.insert(0, s)
                    overlap_len += len(s)
                current = overlap
                current_len = overlap_len

            current.append(sent)
            current_len += len(sent)

        if current:
            chunk_text = " ".join(current)
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    source=source,
                    text=chunk_text,
                )
            )

        return chunks
