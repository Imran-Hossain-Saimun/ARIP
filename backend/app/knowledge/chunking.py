"""§09: chunk_size 800 / overlap 120. Approximated in whitespace-split words rather than
a real tokenizer (tiktoken etc.) — close enough for chunk boundaries in this build, not
byte-for-byte what a production tokenizer would produce."""

CHUNK_SIZE_WORDS = 800
CHUNK_OVERLAP_WORDS = 120


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(words):
        chunk = " ".join(words[start : start + chunk_size])
        chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
        start += step
    return chunks
