from sqlalchemy.orm import Session

from app.ai.providers.embeddings import EmbeddingProvider
from app.knowledge.chunking import chunk_text
from app.knowledge.hierarchy import find_node_for_offset, parse_hierarchy
from app.models.base import utcnow
from app.models.knowledge import KnowledgeChunk, KnowledgeNode, KnowledgeVersion


def index_version(db: Session, version: KnowledgeVersion, embedding_provider: EmbeddingProvider) -> None:
    """Builds the hierarchy tree + pgvector chunks for a version's `content`. Safe to
    call again (e.g. on re-approval) — existing nodes/chunks cascade-delete via the
    version's relationship config before being rebuilt."""
    version.nodes.clear()
    version.chunks.clear()
    db.flush()

    text = version.content
    hierarchy = parse_hierarchy(text)
    db_nodes: list[KnowledgeNode] = []
    for i, node in enumerate(hierarchy):
        db_node = KnowledgeNode(version_id=version.id, title=node.title, locator=node.locator, order_index=i)
        db.add(db_node)
        db_nodes.append(db_node)
    db.flush()
    for i, node in enumerate(hierarchy):
        if node.parent_index is not None:
            db_nodes[i].parent_id = db_nodes[node.parent_index].id
    db.flush()

    pieces = chunk_text(text)
    if pieces:
        embeddings = embedding_provider.embed(pieces)
        search_cursor = 0
        for idx, (piece, embedding) in enumerate(zip(pieces, embeddings)):
            probe = piece[:30]
            offset = text.find(probe, search_cursor) if probe else search_cursor
            if offset == -1:
                offset = search_cursor
            search_cursor = offset + 1
            node_idx = find_node_for_offset(hierarchy, offset)
            db.add(
                KnowledgeChunk(
                    version_id=version.id,
                    node_id=db_nodes[node_idx].id if node_idx is not None else None,
                    chunk_index=idx,
                    content=piece,
                    embedding=embedding,
                )
            )

    version.indexed_at = utcnow()
    db.flush()
