"""Экспорт в формат DOT языка Graphviz.

Координаты вершин записываются в атрибут pos с восклицательным знаком —
так Graphviz не пересчитывает раскладку, а рисует ровно ту укладку, что
построила программа:

    neato -n -Tsvg examples/practice.dot -o practice-graphviz.svg
"""

EDGE_COLORS = {
    "normal": "#38414f",
    "embedded": "#1f8a5f",
    "conflict": "#c0392b",
    "pending": "#b6bec9",
}


def _quote(text):
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_dot(graph, positions=None, edge_style=None, name="G"):
    """DOT-текст графа; positions в пикселях, edge_style как в render."""
    edge_style = edge_style or {}
    lines = [f"graph {_quote(name)} {{",
             '    node [shape="circle", fontname="Helvetica", width="0.45", fixedsize="true"];']
    for v in graph.vertices:
        if positions:
            x, y = positions[v]
            # В Graphviz ось y направлена вверх, в SVG — вниз.
            lines.append(f'    {_quote(v)} [pos="{x:.2f},{-y:.2f}!"];')
        else:
            lines.append(f"    {_quote(v)};")
    for u, v in graph.edges:
        style = edge_style.get((u, v), "normal")
        attrs = [f"color={_quote(EDGE_COLORS[style])}"]
        if style == "conflict":
            attrs.append("penwidth=3")
        if style == "pending":
            attrs.append("style=dashed")
        lines.append(f"    {_quote(u)} -- {_quote(v)} [{', '.join(attrs)}];")
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_dot(path, *args, **kwargs):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(to_dot(*args, **kwargs))
    return path
