"""Builds the "vectorless" hierarchy tree (§08/§09) from markdown-style `#` headings.
Simplified: real heading detection and nesting, but node/chunk association is done by
approximate character-offset containment rather than a proper document AST."""

import re
from dataclasses import dataclass, field

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@dataclass
class HierarchyNode:
    title: str
    locator: str
    start: int
    end: int
    parent_index: int | None
    children: list[int] = field(default_factory=list)


def parse_hierarchy(text: str) -> list[HierarchyNode]:
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [HierarchyNode(title="Document", locator="§1", start=0, end=len(text), parent_index=None)]

    nodes: list[HierarchyNode] = []
    stack: list[tuple[int, int]] = []  # (level, node_index)
    counters: dict[int, int] = {}

    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        while stack and stack[-1][0] >= level:
            stack.pop()
        parent_index = stack[-1][1] if stack else None

        for lvl in list(counters):
            if lvl > level:
                del counters[lvl]
        counters[level] = counters.get(level, 0) + 1
        locator = "§" + ".".join(str(counters[lvl]) for lvl in sorted(counters) if lvl <= level)

        node = HierarchyNode(title=title, locator=locator, start=start, end=end, parent_index=parent_index)
        nodes.append(node)
        if parent_index is not None:
            nodes[parent_index].children.append(len(nodes) - 1)
        stack.append((level, len(nodes) - 1))

    return nodes


def find_node_for_offset(nodes: list[HierarchyNode], offset: int) -> int | None:
    """Deepest node whose span contains `offset`, or None if no heading covers it
    (e.g. preamble text before the first heading)."""
    best: int | None = None
    for i, node in enumerate(nodes):
        if node.start <= offset < node.end:
            if best is None or (node.end - node.start) < (nodes[best].end - nodes[best].start):
                best = i
    return best
