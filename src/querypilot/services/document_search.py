"""Safe local Markdown ingestion and deterministic BM25 passage retrieval."""

import math
import os
import re
import stat
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from querypilot.schemas.documents import (
    DocumentMetadata,
    DocumentSearchInput,
    DocumentSearchOutput,
    SearchHit,
)

MAX_FILES, MAX_BYTES, MAX_CHUNKS, CHUNK_CHARS = 50, 64000, 500, 1200
STOP_WORDS = frozenset(
    (
        "a an and are as at be by can do does for from how i in is it of on or our "
        "that the their these this to we what when where which who with you your"
    ).split()
)


class DocumentError(Exception):
    """A safe collection-level failure; never includes paths or file content."""


@dataclass(frozen=True)
class DocumentChunk:
    metadata: DocumentMetadata
    section: str
    excerpt: str
    citation: str


def tokenize(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return [term for term in re.findall(r"[a-z0-9]+", normalized) if term not in STOP_WORDS]


def _split_text(content: str) -> list[str]:
    parts = []
    remaining = content.strip()
    while remaining:
        cut = len(remaining)
        if cut > CHUNK_CHARS:
            cut = remaining.rfind("\n\n", 0, CHUNK_CHARS + 1)
            if cut < 1:
                cut = remaining.rfind(" ", 0, CHUNK_CHARS + 1)
            if cut < 1:
                cut = CHUNK_CHARS
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    return parts


def parse_document(content: str) -> tuple[DocumentMetadata, list[DocumentChunk]]:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise DocumentError("Invalid business document metadata.")
    try:
        end = lines.index("---", 1)
        fields = {}
        for line in lines[1:end]:
            key, value = line.split(":", 1)
            if key.strip() in fields:
                raise ValueError("Duplicate metadata key")
            fields[key.strip()] = value.strip()
        metadata = DocumentMetadata.model_validate(fields)
    except (ValueError, ValidationError):
        raise DocumentError("Invalid business document metadata.") from None
    chunks: list[DocumentChunk] = []
    heading, section_number = metadata.title, 0
    body: list[str] = []
    fenced = False

    def emit() -> None:
        for index, part in enumerate(_split_text("\n".join(body)), 1):
            if section_number > 999 or index > 999 or len(heading) > 200:
                raise DocumentError("Business document structure exceeds bounds.")
            chunks.append(
                DocumentChunk(
                    metadata,
                    heading,
                    part,
                    f"{metadata.document_id}#s{section_number:03d}-c{index:03d}",
                )
            )

    for line in lines[end + 1 :]:
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line) if not fenced else None
        if match:
            emit()
            heading = match.group(1)
            section_number += 1
            body.clear()
        else:
            body.append(line)
    emit()
    if not chunks:
        return metadata, []
    if section_number == 0:
        raise DocumentError("Business documents require section headings.")
    return metadata, chunks


class DocumentIndex:
    def __init__(self, chunks: list[DocumentChunk], document_count: int, skipped_files: int = 0):
        if len(chunks) > MAX_CHUNKS or document_count > MAX_FILES:
            raise DocumentError("Business document collection exceeds bounds.")
        self.chunks = tuple(sorted(chunks, key=lambda chunk: chunk.citation))
        self.document_count = document_count
        self.skipped_files = skipped_files
        self._counts = tuple(
            Counter(tokenize(f"{chunk.metadata.title} {chunk.section} {chunk.excerpt}"))
            for chunk in self.chunks
        )
        self._lengths = tuple(sum(counts.values()) for counts in self._counts)
        self._average_length = sum(self._lengths) / len(chunks) if chunks else 0
        self._frequencies = Counter(term for counts in self._counts for term in counts)

    @classmethod
    def from_directory(cls, root: Path) -> "DocumentIndex":
        # Root is trusted operator configuration, never a tool argument. Fail closed on
        # platforms without descriptor-relative, no-follow opening support.
        if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
            raise DocumentError("Safe document loading is unavailable on this platform.")
        root_fd = None
        chunks, identifiers, skipped = [], set(), 0
        try:
            root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            names = sorted(os.listdir(root_fd))
            candidates = [name for name in names if Path(name).suffix.lower() == ".md"]
            if len(candidates) > MAX_FILES:
                raise DocumentError("Business document collection exceeds bounds.")
            skipped += len(names) - len(candidates)
            for name in candidates:
                descriptor = None
                try:
                    descriptor = os.open(
                        name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd
                    )
                    info = os.fstat(descriptor)
                    if (
                        not stat.S_ISREG(info.st_mode)
                        or info.st_nlink != 1
                        or info.st_size > MAX_BYTES
                    ):
                        raise OSError("Unsafe document entry")
                    with os.fdopen(descriptor, "rb") as source:
                        descriptor = None
                        raw = source.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        raise OSError("Oversized document")
                    content = raw.decode("utf-8")
                except (OSError, UnicodeError):
                    skipped += 1
                    continue
                finally:
                    if descriptor is not None:
                        os.close(descriptor)
                if not content.strip():
                    skipped += 1
                    continue
                metadata, passages = parse_document(content)
                if metadata.document_id in identifiers:
                    raise DocumentError("Duplicate business document identifiers.")
                if not passages:
                    skipped += 1
                    continue
                identifiers.add(metadata.document_id)
                chunks.extend(passages)
                if len(chunks) > MAX_CHUNKS:
                    raise DocumentError("Business document collection exceeds bounds.")
        except OSError:
            raise DocumentError("Business document collection is unavailable.") from None
        finally:
            if root_fd is not None:
                os.close(root_fd)
        return cls(chunks, len(identifiers), skipped)

    def search(self, arguments: DocumentSearchInput) -> DocumentSearchOutput:
        terms = sorted(set(tokenize(arguments.query)))
        ranked = []
        size = len(self.chunks)
        if terms and size and self._average_length:
            for chunk, counts, length in zip(self.chunks, self._counts, self._lengths, strict=True):
                if arguments.category is not None and chunk.metadata.category != arguments.category:
                    continue
                score = 0.0
                for term in terms:
                    frequency = counts.get(term, 0)
                    if frequency:
                        document_frequency = self._frequencies[term]
                        idf = math.log1p(
                            (size - document_frequency + 0.5) / (document_frequency + 0.5)
                        )
                        score += (
                            idf
                            * frequency
                            * 2.5
                            / (frequency + 1.5 * (0.25 + 0.75 * length / self._average_length))
                        )
                if score > 0:
                    ranked.append((score, chunk))
        ranked.sort(key=lambda pair: (-pair[0], pair[1].citation))
        matches = [
            SearchHit(
                document_id=chunk.metadata.document_id,
                document_title=chunk.metadata.title,
                category=chunk.metadata.category,
                section=chunk.section,
                excerpt=chunk.excerpt,
                score=round(score, 8),
                source_citation=chunk.citation,
            )
            for score, chunk in ranked[: arguments.top_k]
        ]
        return DocumentSearchOutput(
            matches=matches, indexed_documents=self.document_count, indexed_chunks=size
        )
