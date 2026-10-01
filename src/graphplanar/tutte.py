"""Геометрическая укладка алгоритмом Тутте (барицентрическое вложение).

Тутте: если граф 3-связен и планарен, а вершины одной его грани закрепить
на выпуклом многоугольнике, то, поместив каждую остальную вершину в центр
масс её соседей, получим плоский рисунок прямыми отрезками без
пересечений. Координаты свободных вершин находятся из системы линейных
уравнений
    deg(v) · p(v) − Σ p(u) = 0      по соседям u вершины v.

Произвольный планарный граф 3-связным не является, поэтому перед
применением Тутте граф достраивается:

1. компоненты связности рисуются по отдельности;
2. связная компонента достраивается до двусвязной рёбрами, проведёнными
   внутри граней (см. embedding.make_biconnected) — теперь каждая грань
   ограничена простым циклом;
3. самая длинная грань выбирается внешней, её вершины ставятся на
   правильный многоугольник;
4. в каждую внутреннюю грань длиннее трёх добавляется вспомогательная
   вершина, соединённая со всеми вершинами грани, — после этого все
   внутренние грани треугольники.

Получается триангуляция диска с выпуклой границей. Для неё барицентрическое
отображение взаимно однозначно (теорема Тутте в обобщении Флоатера), так
что рисунок получается плоским. В конце вспомогательные вершины и рёбра
убираются: подграф плоского рисунка тоже плоский.
"""

import math

from .embedding import face_walk, make_biconnected


class DrawingInfo:
    """Что пришлось сделать, чтобы нарисовать граф."""

    def __init__(self):
        self.added_edges = []       # рёбра, добавленные для двусвязности
        self.dummy_vertices = 0     # вспомогательные вершины в гранях
        self.outer_faces = []       # внешняя грань каждой компоненты
        self.relax_moves = 0        # принятых перемещений при раздвигании
        self.relax_skipped = False  # раздвигание пропущено из-за размера графа


def _solve(matrix, rhs):
    """Метод Гаусса с выбором главного элемента для нескольких правых частей."""
    n = len(matrix)
    a = [row[:] + list(values) for row, values in zip(matrix, rhs)]
    width = len(a[0])
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ArithmeticError("система уравнений Тутте вырождена")
        a[col], a[pivot] = a[pivot], a[col]
        lead = a[col][col]
        for j in range(col, width):
            a[col][j] /= lead
        for r in range(n):
            if r != col and a[r][col]:
                factor = a[r][col]
                row_r, row_c = a[r], a[col]
                for j in range(col, width):
                    row_r[j] -= factor * row_c[j]
    return [row[n:] for row in a]


def barycentric(adjacency, fixed):
    """Решить систему Тутте: свободные вершины — в центрах масс соседей."""
    free = [v for v in adjacency if v not in fixed]
    index = {v: i for i, v in enumerate(free)}
    matrix = [[0.0] * len(free) for _ in free]
    rhs = [[0.0, 0.0] for _ in free]
    for v in free:
        i = index[v]
        matrix[i][i] = float(len(adjacency[v]))
        for u in adjacency[v]:
            if u in index:
                matrix[i][index[u]] -= 1.0
            else:
                rhs[i][0] += fixed[u][0]
                rhs[i][1] += fixed[u][1]

    positions = dict(fixed)
    if free:
        solution = _solve(matrix, rhs)
        for v in free:
            positions[v] = tuple(solution[index[v]])
    return positions


def _component_layout(component_graph, rotation, info, relax_enabled=True):
    """Координаты вершин одной связной компоненты в круге радиуса 1."""
    vertices = component_graph.vertices
    if len(vertices) == 1:
        info.outer_faces.append(list(vertices))
        return {vertices[0]: (0.0, 0.0)}
    if len(vertices) == 2:
        info.outer_faces.append(list(vertices))
        return {vertices[0]: (-0.6, 0.0), vertices[1]: (0.6, 0.0)}

    augmented, rotation, added = make_biconnected(component_graph, rotation)
    info.added_edges.extend(added)
    faces = face_walk(rotation)

    # Внешнюю грань выбираем перебором: Тутте даёт плоский рисунок при
    # любом выборе, но читаемость сильно зависит от него. Оставляем рисунок,
    # где вершины дальше всего друг от друга и от чужих рёбер.
    candidates = sorted(range(len(faces)), key=lambda i: -len(faces[i]))[:MAX_OUTER_CANDIDATES]
    best = None
    for index in candidates:
        positions, dummies = _tutte_with_outer(augmented, faces, index)
        score = layout_quality({v: positions[v] for v in vertices}, component_graph.edges)
        if best is None or score > best[0] + 1e-12:
            best = (score, index, positions, dummies)

    _, index, positions, dummies = best
    outer = faces[index]
    info.outer_faces.append(list(outer))
    info.dummy_vertices += dummies
    layout = {v: positions[v] for v in vertices}

    if relax_enabled and len(vertices) > RELAX_LIMIT:
        info.relax_skipped = True
    elif relax_enabled:
        from .relax import relax
        relaxed, moves = relax(layout, component_graph.edges, set(outer),
                               [layout[v] for v in outer])
        # Раздвигание берём, только если самый тесный зазор не уменьшился.
        edges = component_graph.edges
        if layout_quality(relaxed, edges) >= layout_quality(layout, edges) - 1e-12:
            layout = relaxed
            info.relax_moves += moves
    return layout


MAX_OUTER_CANDIDATES = 24

# Раздвигание перепроверяет все рёбра на каждом шаге, поэтому на больших
# графах оно долгое; рисунок Тутте и без него плоский.
RELAX_LIMIT = 40


def _tutte_with_outer(augmented, faces, outer_index):
    """Барицентрическая укладка при заданной внешней грани.

    Возвращает (позиции, число вспомогательных вершин).
    """
    outer = faces[outer_index]
    adjacency = {v: set(augmented.neighbors(v)) for v in augmented.vertices}
    dummies = 0
    for number, face in enumerate(faces):
        if number == outer_index or len(face) <= 3:
            continue
        dummy = ("вспомогательная", number)
        adjacency[dummy] = set(face)
        for v in face:
            adjacency[v].add(dummy)
        dummies += 1

    count = len(outer)
    fixed = {}
    for k, v in enumerate(outer):
        angle = math.pi / 2 + 2 * math.pi * k / count
        fixed[v] = (math.cos(angle), -math.sin(angle))
    return barycentric(adjacency, fixed), dummies


def layout_quality(positions, edges):
    """Насколько рисунок читаем: наименьшее из расстояний между вершинами
    и от вершины до не своего ребра. Чем больше, тем лучше."""
    from .geometry import point_segment_distance

    vertices = list(positions)
    best = float("inf")
    for i, u in enumerate(vertices):
        for v in vertices[i + 1:]:
            best = min(best, math.dist(positions[u], positions[v]))
    for a, b in edges:
        for v in vertices:
            if v != a and v != b:
                best = min(best, point_segment_distance(positions[v], positions[a], positions[b]))
    return best


def tutte_layout(graph, rotation, components, relax_enabled=True):
    """Плоский рисунок всего графа: компоненты ставятся в ряд.

    graph      — исходный граф
    rotation   — система вращений из комбинаторной укладки
    components — компоненты связности (списки вершин)
    relax_enabled — после Тутте раздвинуть вершины, сохраняя планарность

    Возвращает (позиции, DrawingInfo). Координаты безразмерные, масштаб
    задаёт рендер.
    """
    from .graph import Graph

    info = DrawingInfo()
    positions = {}
    offset = 0.0
    for component in components:
        members = set(component)
        sub = Graph()
        for v in component:
            sub.add_vertex(v)
        for u, v in graph.edges:
            if u in members:
                sub.add_edge(u, v)
        sub_rotation = {v: rotation[v] for v in component}

        layout = _component_layout(sub, sub_rotation, info, relax_enabled)
        min_x = min(x for x, _ in layout.values())
        max_x = max(x for x, _ in layout.values())
        for v, (x, y) in layout.items():
            positions[v] = (x - min_x + offset, y)
        offset += (max_x - min_x) + 0.9

    return positions, info
