"""Комбинаторная укладка: система вращений и грани.

Система вращений задаёт для каждой вершины циклический порядок её соседей.
Этого достаточно, чтобы однозначно описать, как граф лежит на плоскости:
грани восстанавливаются обходом.

Соглашение об обходе граней. Дуга (a, b) — ребро, пройденное от a к b.
Следующая дуга в той же грани — (b, c), где c — сосед, идущий в списке
вращения вершины b сразу после a (по циклу).
"""

from .blocks import biconnected_components, block_vertices, connected_components, edge_key
from .demoucron import embed_block
from .graph import Graph


class PlanarityResult:
    """Итог проверки планарности всего графа."""

    def __init__(self, graph):
        self.graph = graph
        self.planar = True
        self.components = []
        self.blocks = []
        self.cut_vertices = set()
        self.block_results = []     # (рёбра блока, BlockEmbedding или None для моста)
        self.failure = None         # (рёбра блока, BlockEmbedding) при непланарности
        self.rotation = {}
        self.faces = []


def rotation_from_faces(faces):
    """Восстановить систему вращений по согласованно ориентированным граням.

    Если в грани идут подряд вершины a, b, c, то по соглашению об обходе
    сосед c следует в списке вращения вершины b сразу за a.
    """
    successor = {}
    for face in faces:
        size = len(face)
        for i in range(size):
            a, b, c = face[i - 1], face[i], face[(i + 1) % size]
            successor.setdefault(b, {})[a] = c

    rotation = {}
    for vertex, following in successor.items():
        start = min(following)
        order = [start]
        current = following[start]
        while current != start:
            order.append(current)
            current = following[current]
        if len(order) != len(following):
            raise AssertionError(f"грани вокруг вершины {vertex} не образуют один цикл")
        rotation[vertex] = order
    return rotation


def face_walk(rotation):
    """Все грани укладки, заданной системой вращений.

    Каждая дуга проходится ровно один раз; грань — последовательность
    вершин, из которых выходят её дуги.
    """
    position = {v: {u: i for i, u in enumerate(order)} for v, order in rotation.items()}
    visited = set()
    faces = []
    for start in sorted(rotation):
        for neighbor in rotation[start]:
            if (start, neighbor) in visited:
                continue
            face = []
            a, b = start, neighbor
            while (a, b) not in visited:
                visited.add((a, b))
                face.append(a)
                order = rotation[b]
                c = order[(position[b][a] + 1) % len(order)]
                a, b = b, c
            faces.append(face)
    return faces


def euler_characteristic(vertex_count, edge_count, face_count):
    return vertex_count - edge_count + face_count


def check_planarity(graph):
    """Проверить планарность графа и построить комбинаторную укладку.

    Схема: граф разбивается на блоки, каждый блок с циклом проверяется
    алгоритмом Демукрона, мосты (блоки из одного ребра) планарны всегда.
    Укладки блоков склеиваются в точках сочленения: списки вращения
    вершины из разных блоков просто записываются подряд. Это соответствует
    тому, что один блок кладётся в грань другого, и планарности не
    нарушает — формула Эйлера для склейки сохраняется.
    """
    result = PlanarityResult(graph)
    result.components = connected_components(graph)
    result.blocks, result.cut_vertices = biconnected_components(graph)

    rotation = {v: [] for v in graph.vertices}
    for block in result.blocks:
        if len(block) == 1:
            (u, v), = block
            rotation[u].append(v)
            rotation[v].append(u)
            result.block_results.append((block, None))
            continue

        embedding = embed_block(block)
        result.block_results.append((block, embedding))
        if not embedding.planar:
            result.planar = False
            result.failure = (block, embedding)
            return result

        block_rotation = rotation_from_faces(embedding.faces)
        for vertex in block_vertices(block):
            rotation[vertex].extend(block_rotation[vertex])

    result.rotation = rotation
    result.faces = face_walk(rotation)
    return result


def faces_per_component(result):
    """Для каждой компоненты: (вершины, число рёбер, число граней)."""
    face_owner = {}
    for index, component in enumerate(result.components):
        for v in component:
            face_owner[v] = index
    counts = [0] * len(result.components)
    for face in result.faces:
        counts[face_owner[face[0]]] += 1

    report = []
    for index, component in enumerate(result.components):
        members = set(component)
        edges = sum(1 for u, v in result.graph.edges if u in members)
        faces = counts[index] if edges else 1   # у изолированной вершины одна грань
        report.append((component, edges, faces))
    return report


def make_biconnected(graph, rotation):
    """Достроить связный планарный граф до двусвязного, сохранив укладку.

    Пока есть точка сочленения v, ищем в её списке вращения двух соседних
    соседей u и w, рёбра к которым лежат в разных блоках. Угол u – v – w
    принадлежит одной грани, поэтому ребро [u, w] можно провести по этой
    грани без пересечений. Оно объединяет блоки, и точек сочленения
    становится меньше. Смежны u и w быть не могут: иначе треугольник
    u – v – w лежал бы в одном блоке.

    Возвращает (новый граф, новую систему вращений, добавленные рёбра).
    """
    augmented = Graph()
    for v in graph.vertices:
        augmented.add_vertex(v)
    for u, v in graph.edges:
        augmented.add_edge(u, v)
    rotation = {v: list(order) for v, order in rotation.items()}
    added = []

    while True:
        blocks, cut_vertices = biconnected_components(augmented)
        if not cut_vertices:
            return augmented, rotation, added

        block_of = {}
        for index, block in enumerate(blocks):
            for edge in block:
                block_of[edge] = index

        v = min(cut_vertices)
        order = rotation[v]
        for i in range(len(order)):
            u, w = order[i], order[(i + 1) % len(order)]
            if block_of[edge_key(v, u)] != block_of[edge_key(v, w)]:
                break

        # Новое ребро проходит внутри грани с углом u – v – w:
        # у w сосед u встаёт сразу после v, у u сосед w — сразу перед v.
        rotation[w].insert(rotation[w].index(v) + 1, u)
        rotation[u].insert(rotation[u].index(v), w)
        augmented.add_edge(u, w)
        added.append(edge_key(u, w))
