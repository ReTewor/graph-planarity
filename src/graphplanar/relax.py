"""Раздвигание вершин после укладки Тутте с сохранением планарности.

Рисунок Тутте всегда плоский, но вершины в глубине часто сжаты в кучку.
Здесь рисунок улучшается силовым методом (Фрухтерман — Рейнгольд):
вершины отталкиваются друг от друга, а рёбра притягивают свои концы.

Главное отличие от обычного силового метода: каждое перемещение вершины
сначала проверяется и принимается, только если
  - её рёбра ни с чем не пересекаются,
  - она остаётся внутри внешнего многоугольника,
  - она не подходит к чужим рёбрам и вершинам ближе, чем была.
Поэтому планарность рисунка сохраняется на каждом шаге, а вершины внешней
грани вообще не двигаются.
"""

import math

from .geometry import point_segment_distance, segments_intersect


def _inside_convex(point, polygon, margin):
    """Лежит ли точка внутри выпуклого многоугольника с отступом margin."""
    count = len(polygon)
    if count < 3:
        return True
    sign = 0
    for i in range(count):
        a, b = polygon[i], polygon[(i + 1) % count]
        cross = (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])
        distance = cross / (math.dist(a, b) or 1.0)
        if abs(distance) < margin:
            return False
        current = 1 if distance > 0 else -1
        if sign == 0:
            sign = current
        elif current != sign:
            return False
    return True


def _clearance(v, point, positions, adjacency, edges):
    """Наименьшее расстояние от вершины v (в точке point) и её рёбер
    до чужих вершин и рёбер."""
    best = float("inf")
    for w, other in positions.items():
        if w != v:
            best = min(best, math.dist(point, other))
    for a, b in edges:
        if v not in (a, b):
            best = min(best, point_segment_distance(point, positions[a], positions[b]))
    for u in adjacency[v]:
        for w, other in positions.items():
            if w not in (v, u):
                best = min(best, point_segment_distance(other, point, positions[u]))
    return best


def _crosses(v, point, positions, adjacency, edges):
    for u in adjacency[v]:
        for a, b in edges:
            if a in (v, u) or b in (v, u):
                continue
            if segments_intersect(point, positions[u], positions[a], positions[b]):
                return True
    return False


def relax(positions, edges, fixed, outer_polygon, iterations=120,
          temperature=0.12, cooling=0.96):
    """Улучшить расстановку, не нарушая планарности.

    positions      — плоский рисунок (координаты в круге радиуса 1)
    edges          — рёбра графа
    fixed          — вершины, которые не двигаются (внешняя грань)
    outer_polygon  — координаты внешней грани по порядку

    Возвращает (новые позиции, число принятых перемещений).
    """
    positions = dict(positions)
    adjacency = {v: set() for v in positions}
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)

    free = [v for v in positions if v not in fixed]
    if not free:
        return positions, 0

    k = 1.6 / math.sqrt(len(positions))      # желаемая длина ребра
    # Ближе этого вершины сдвигать друг к другу и к рёбрам нельзя, если
    # они и так не стояли ближе.
    target = 0.45 * k
    accepted = 0

    for _ in range(iterations):
        force = {v: [0.0, 0.0] for v in free}
        for v in free:
            x, y = positions[v]
            for w, (ox, oy) in positions.items():
                if w == v:
                    continue
                dx, dy = x - ox, y - oy
                distance = math.hypot(dx, dy) or 1e-9
                push = k * k / distance
                force[v][0] += dx / distance * push
                force[v][1] += dy / distance * push
            for u in adjacency[v]:
                ox, oy = positions[u]
                dx, dy = x - ox, y - oy
                distance = math.hypot(dx, dy) or 1e-9
                pull = distance * distance / k
                force[v][0] -= dx / distance * pull
                force[v][1] -= dy / distance * pull

        largest_step = 0.0
        for v in free:
            fx, fy = force[v]
            length = math.hypot(fx, fy)
            if length < 1e-12:
                continue
            step = min(length, temperature)
            candidate = (positions[v][0] + fx / length * step,
                         positions[v][1] + fy / length * step)
            if not _inside_convex(candidate, outer_polygon, 0.02):
                continue
            before = _clearance(v, positions[v], positions, adjacency, edges)
            after = _clearance(v, candidate, positions, adjacency, edges)
            if after < min(before, target):
                continue
            if _crosses(v, candidate, positions, adjacency, edges):
                continue
            positions[v] = candidate
            accepted += 1
            largest_step = max(largest_step, step)

        temperature *= cooling
        if largest_step < 1e-4:
            break

    return positions, accepted
