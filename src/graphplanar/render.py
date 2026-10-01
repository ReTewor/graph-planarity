"""Собственная визуализация в SVG — без Graphviz и других библиотек.

SVG собирается как текст. Рёбра укорачиваются на радиус вершины, чтобы
линия начиналась на границе кружка, а не уходила под него.
"""

import math

PALETTE = {
    "background": "#ffffff",
    "text": "#1d232c",
    "caption": "#5a6472",
    "vertex_fill": "#eef2f7",
    "vertex_stroke": "#38414f",
}

EDGE_STYLES = {
    "normal": {"color": "#38414f", "width": 1.8, "dash": None},
    "embedded": {"color": "#1f8a5f", "width": 2.6, "dash": None},
    "conflict": {"color": "#c0392b", "width": 3.0, "dash": None},
    "pending": {"color": "#b6bec9", "width": 1.3, "dash": "5 4"},
}

VERTEX_STYLES = {
    "normal": ("#eef2f7", "#38414f"),
    "embedded": ("#d6f0e3", "#1f8a5f"),
    "conflict": ("#fbe1dd", "#c0392b"),
}

FONT = "Helvetica, Arial, DejaVu Sans, sans-serif"


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _trim(x1, y1, x2, y2, radius):
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length <= 2 * radius:
        return x1, y1, x2, y2
    ux, uy = dx / length, dy / length
    return x1 + ux * radius, y1 + uy * radius, x2 - ux * radius, y2 - uy * radius


def fit_positions(positions, unit=220.0):
    """Перевести безразмерные координаты в пиксели.

    Масштаб фиксированный: единица длины — unit пикселей. Каждая
    компонента укладывается в круг радиуса 1, поэтому граф из нескольких
    компонент получается шире, а не мельче.
    """
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    return {v: ((x - min(xs)) * unit, (y - min(ys)) * unit) for v, (x, y) in positions.items()}


def circular_positions(vertices, radius=240.0):
    count = len(vertices)
    return {
        v: (radius * math.cos(2 * math.pi * i / count - math.pi / 2),
            radius * math.sin(2 * math.pi * i / count - math.pi / 2))
        for i, v in enumerate(vertices)
    }


def render_svg(graph, positions, edge_style=None, vertex_style=None,
               title=None, caption_lines=(), legend=(), radius=17, margin=40):
    """Нарисовать граф.

    positions     — координаты вершин в пикселях
    edge_style    — {ребро: стиль из EDGE_STYLES}, по умолчанию "normal"
    vertex_style  — {вершина: стиль из VERTEX_STYLES}
    caption_lines — строки подписи под рисунком
    legend        — пары (стиль ребра, пояснение)
    """
    edge_style = edge_style or {}
    vertex_style = vertex_style or {}

    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    top = margin + (32 if title else 0)
    legend_height = 24 * len(legend)
    caption_height = 20 * len(caption_lines)
    bottom = margin + legend_height + caption_height + (12 if legend or caption_lines else 0)
    shift_x = margin + radius - min(xs)
    shift_y = top + radius - min(ys)
    content = (max(xs) - min(xs)) + 2 * (margin + radius)
    title_width = len(title) * 10 + 2 * margin if title else 0
    legend_width = max((len(text) * 7.4 + 44 + 2 * margin for _, text in legend), default=0)
    width = max(content, title_width, legend_width, 460)
    height = (max(ys) - min(ys)) + 2 * radius + top + bottom
    shift_x += (width - content) / 2

    def place(v):
        x, y = positions[v]
        return x + shift_x, y + shift_y

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}">',
        f'  <rect width="100%" height="100%" fill="{PALETTE["background"]}"/>',
    ]
    if title:
        parts.append(
            f'  <text x="{width / 2:.1f}" y="{margin:.1f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="17" font-weight="600" '
            f'fill="{PALETTE["text"]}">{_escape(title)}</text>'
        )

    order = ["pending", "normal", "embedded", "conflict"]
    for style_name in order:
        style = EDGE_STYLES[style_name]
        for u, v in graph.edges:
            if edge_style.get((u, v), "normal") != style_name:
                continue
            x1, y1 = place(u)
            x2, y2 = place(v)
            a, b, c, d = _trim(x1, y1, x2, y2, radius)
            dash = f' stroke-dasharray="{style["dash"]}"' if style["dash"] else ""
            parts.append(
                f'  <line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" '
                f'stroke="{style["color"]}" stroke-width="{style["width"]}" '
                f'stroke-linecap="round"{dash}/>'
            )

    for v in graph.vertices:
        x, y = place(v)
        fill, stroke = VERTEX_STYLES[vertex_style.get(v, "normal")]
        parts.append(
            f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.7"/>'
        )
        parts.append(
            f'  <text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="central" '
            f'font-family="{FONT}" font-size="14" fill="{PALETTE["text"]}">{_escape(v)}</text>'
        )

    y = height - bottom + 12
    for style_name, text in legend:
        style = EDGE_STYLES[style_name]
        dash = f' stroke-dasharray="{style["dash"]}"' if style["dash"] else ""
        parts.append(
            f'  <line x1="{margin:.1f}" y1="{y + 8:.1f}" x2="{margin + 34:.1f}" y2="{y + 8:.1f}" '
            f'stroke="{style["color"]}" stroke-width="{style["width"]}"{dash}/>'
        )
        parts.append(
            f'  <text x="{margin + 44:.1f}" y="{y + 8:.1f}" dominant-baseline="central" '
            f'font-family="{FONT}" font-size="13" fill="{PALETTE["caption"]}">{_escape(text)}</text>'
        )
        y += 24
    for line in caption_lines:
        parts.append(
            f'  <text x="{width / 2:.1f}" y="{y + 10:.1f}" text-anchor="middle" '
            f'dominant-baseline="central" font-family="{FONT}" font-size="13" '
            f'fill="{PALETTE["caption"]}">{_escape(line)}</text>'
        )
        y += 20

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def write_svg(path, *args, **kwargs):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_svg(*args, **kwargs))
    return path
