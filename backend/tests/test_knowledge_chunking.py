from app.knowledge.chunking import chunk_text
from app.knowledge.hierarchy import find_node_for_offset, parse_hierarchy


def test_chunk_text_splits_long_text_with_overlap():
    words = [f"word{i}" for i in range(2000)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=800, overlap=120)

    assert len(chunks) > 1
    # consecutive chunks overlap by roughly `overlap` words
    first_words = chunks[0].split()
    second_words = chunks[1].split()
    assert first_words[-1] != second_words[0]  # sanity: not identical single word
    overlap_words = set(first_words[-120:])
    assert overlap_words & set(second_words[:120])


def test_chunk_text_returns_single_chunk_for_short_text():
    assert chunk_text("just a few words here") == ["just a few words here"]


def test_chunk_text_empty_string_returns_no_chunks():
    assert chunk_text("") == []


def test_parse_hierarchy_builds_nested_headings():
    text = "# Intro\nSome preamble.\n## Details\nMore text.\n# Conclusion\nThe end."
    nodes = parse_hierarchy(text)

    titles = [n.title for n in nodes]
    assert titles == ["Intro", "Details", "Conclusion"]
    assert nodes[0].locator == "§1"
    assert nodes[1].locator == "§1.1"
    assert nodes[2].locator == "§2"
    assert nodes[1].parent_index == 0


def test_parse_hierarchy_falls_back_to_single_document_node_without_headings():
    nodes = parse_hierarchy("Just plain text, no markdown headings at all.")
    assert len(nodes) == 1
    assert nodes[0].title == "Document"


def test_find_node_for_offset_picks_the_deepest_matching_node():
    text = "# A\nfoo\n## B\nbar"
    nodes = parse_hierarchy(text)
    b_start = text.index("## B")
    idx = find_node_for_offset(nodes, b_start + 1)
    assert nodes[idx].title == "B"
