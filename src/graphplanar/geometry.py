"""Проверка, что рисунок действительно плоский.

Проверяются три вещи:
  1. никакие две вершины не совпадают;
  2. рёбра без общих концов не пересекаются и не касаются;
  3. ни одна вершина не лежит на ребре, которому она не принадлежит
     (это же ловит наложение рёбер с общим концом).
"""

import math


def _side(p, q, r, eps):
    """С какой стороны от прямой pq лежит точка r: +1, −1 или 0 (на прямой).

    Сравнивается синус угла между pq и pr, а не удвоенная площадь
    треугольника. Площадь зависит от масштаба: у метода Тутте вершины в
    глубине рисунка могут стоять на расстоянии 1e-5 друг от друга, и
    абсолютный допуск там признал бы «лежащими на одной прямой» точки,
    которые на ней не лежат.
    """
    cross = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    scale = math.dist(p, q) * math.dist(p, r)
    if scale == 0 or abs(cross) <= eps * scale:
        return 0
    return 1 if cross > 0 else -1


def _within_box(p, q, r):
    """Лежит ли точка r в прямоугольнике, натянутом на отрезок pq."""
    return (
        min(p[0], q[0]) <= r[0] <= max(p[0], q[0])
        and min(p[1], q[1]) <= r[1] <= max(p[1], q[1])
    )


def segments_intersect(p1, p2, p3, p4, eps=1e-10):
    """Пересекаются ли (или касаются) отрезки p1p2 и p3p4."""
    d1 = _side(p3, p4, p1, eps)
    d2 = _side(p3, p4, p2, eps)
    d3 = _side(p1, p2, p3, eps)
    d4 = _side(p1, p2, p4, eps)
    if d1 * d2 < 0 and d3 * d4 < 0:
        return True
    if d1 == 0 and _within_box(p3, p4, p1):
        return True
    if d2 == 0 and _within_box(p3, p4, p2):
        return True
    if d3 == 0 and _within_box(p1, p2, p3):
        return True
    if d4 == 0 and _within_box(p1, p2, p4):
        return True
    return False


def point_segment_distance(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def drawing_defects(positions, edges, eps=1e-10):
    """Список нарушений плоскостности рисунка. Пустой список — рисунок плоский.

    Допуск eps относительный: точка считается лежащей на ребре, если
    расстояние до него меньше eps, умноженного на длину ребра.
    """
    defects = []
    vertices = sorted(positions)

    for i, u in enumerate(vertices):
        for v in vertices[i + 1:]:
            if math.dist(positions[u], positions[v]) <= 1e-13:
                defects.append(f"вершины {u} и {v} совпадают")

    for i, (a, b) in enumerate(edges):
        for c, d in edges[i + 1:]:
            if {a, b} & {c, d}:
                continue
            if segments_intersect(positions[a], positions[b],
                                  positions[c], positions[d], eps):
                defects.append(f"рёбра [{a}, {b}] и [{c}, {d}] пересекаются")

    for a, b in edges:
        for v in vertices:
            if v in (a, b):
                continue
            length = math.dist(positions[a], positions[b])
            if point_segment_distance(positions[v], positions[a], positions[b]) <= eps * length:
                defects.append(f"вершина {v} лежит на ребре [{a}, {b}]")

    return defects
