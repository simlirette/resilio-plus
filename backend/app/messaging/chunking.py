"""Content-preserving message chunking."""

import re
from collections.abc import Iterator

_FENCE_START = re.compile(r"^[ \t]*(`{3,})")
_BULLET_LINE = re.compile(r"^[ \t]*(?:[-+*][ \t]+|\d+[.)][ \t]+)")
_PARAGRAPH_BOUNDARY = re.compile(r"\r?\n[ \t]*\r?\n")
_SENTENCE_BOUNDARY = re.compile(r"[.!?](?:[\"')\]]*)[ \t\r\n]+")


def chunk_message(text: str, max_length: int) -> list[str]:
    """Split *text* without losing content or splitting protected Markdown.

    Fenced code blocks and individual bullet/list lines are emitted atomically.
    Consequently, a protected unit longer than ``max_length`` is returned as one
    intentionally oversized chunk rather than being split.
    """
    if max_length <= 0:
        raise ValueError("max_length must be positive")
    if not text:
        return []
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    pending = ""
    for unit, protected in _iter_units(text):
        if protected:
            pending = _pack_fragment(chunks, pending, unit, max_length)
            continue

        ordinary_chunks = _chunk_ordinary_text(unit, max_length)
        for index, fragment in enumerate(ordinary_chunks):
            pending = _pack_fragment(chunks, pending, fragment, max_length)
            if index < len(ordinary_chunks) - 1:
                chunks.append(pending)
                pending = ""
    if pending:
        chunks.append(pending)
    return chunks


def _iter_units(text: str) -> Iterator[tuple[str, bool]]:
    """Yield ordinary spans and atomic Markdown spans in source order."""
    ordinary_lines: list[str] = []
    code_lines: list[str] = []
    fence_width: int | None = None

    for line in text.splitlines(keepends=True):
        if fence_width is not None:
            code_lines.append(line)
            if _is_closing_fence(line, fence_width):
                yield "".join(code_lines), True
                code_lines = []
                fence_width = None
            continue

        opening_width = _opening_fence_width(line)
        if opening_width is not None:
            if ordinary_lines:
                yield "".join(ordinary_lines), False
                ordinary_lines = []
            code_lines = [line]
            fence_width = opening_width
        elif _BULLET_LINE.match(line):
            if ordinary_lines:
                yield "".join(ordinary_lines), False
                ordinary_lines = []
            yield line, True
        else:
            ordinary_lines.append(line)

    if code_lines:
        yield "".join(code_lines), True
    if ordinary_lines:
        yield "".join(ordinary_lines), False


def _opening_fence_width(line: str) -> int | None:
    match = _FENCE_START.match(line)
    if match is None:
        return None
    return len(match.group(1))


def _is_closing_fence(line: str, opening_width: int) -> bool:
    match = _FENCE_START.match(line)
    if match is None or len(match.group(1)) < opening_width:
        return False
    trailing_text = line[match.end() :]
    return not trailing_text.strip(" \t\r\n")


def _pack_fragment(
    chunks: list[str],
    pending: str,
    fragment: str,
    max_length: int,
) -> str:
    if len(fragment) > max_length:
        if pending:
            chunks.append(pending)
        chunks.append(fragment)
        return ""
    if pending and len(pending) + len(fragment) > max_length:
        chunks.append(pending)
        return fragment
    return pending + fragment


def _chunk_ordinary_text(text: str, max_length: int) -> list[str]:
    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_length:
        window = remaining[:max_length]
        cut_at = _last_boundary(_PARAGRAPH_BOUNDARY, window)
        if cut_at is None:
            cut_at = _last_boundary(_SENTENCE_BOUNDARY, window)
        if cut_at is None:
            cut_at = max_length
        chunks.append(remaining[:cut_at])
        remaining = remaining[cut_at:]
    if remaining:
        chunks.append(remaining)
    return chunks


def _last_boundary(pattern: re.Pattern[str], text: str) -> int | None:
    boundary = None
    for match in pattern.finditer(text):
        boundary = match.end()
    return boundary
