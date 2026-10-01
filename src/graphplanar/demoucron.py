"""Алгоритм Демукрона — проверка планарности двусвязного графа.

Идея: плоская укладка наращивается целыми «мостами». Пусть H — уже
уложенный подграф. Мост относительно H — это либо ребро не из H с обоими
концами в H, либо компонента связности графа G − H вместе с рёбрами,
соединяющими её с H. Вершины моста, лежащие в H, называются контактными.

1. Найти в G любой цикл и уложить его: получаются две грани.
2. Пока уложены не все рёбра:
   - построить все мосты относительно H;
   - для каждого моста B найти множество F(B) граней, на границе которых
     лежат все его контактные вершины;
   - если для какого-то моста F(B) пусто — граф непланарен;
   - если есть мост с |F(B)| = 1 — уложить его в эту единственную грань,
     иначе уложить любой мост в любую подходящую грань;
   - «уложить мост» — провести в грани цепь моста между двумя его
     контактными вершинами; грань разбивается на две.

Грани хранятся как циклические списки вершин и ориентированы
согласованно: каждое ребро входит в две грани в противоположных
направлениях. Это позволяет потом восстановить систему вращений.

Сложность O(n²) на граф с O(n) рёбрами.
"""

from collections import deque

from .blocks import edge_key


class Bridge:
    """Мост относительно уложенного подграфа."""

    def __init__(self, edges, inner, contacts):
        self.edges = edges          # рёбра моста
        self.inner = inner          # вершины моста вне H (у ребра-моста их нет)
        self.contacts = contacts    # контактные вершины, лежащие в H

    def describe(self):
        if not self.inner:
            u, v = sorted(self.contacts)
            return f"ребро [{u}, {v}]"
        inner = ", ".join(str(v) for v in sorted(self.inner))
        return f"компонента {{{inner}}}"


class Step:
    """Запись об одном шаге алгоритма — для пояснений в выводе."""

    def __init__(self, bridge, fits, face, path):
        self.bridge = bridge
        self.fits = fits            # сколько граней подходило мосту
        self.face = face            # грань, в которую уложили
        self.path = path            # уложенная цепь


class BlockEmbedding:
    """Результат работы алгоритма на одном двусвязном блоке."""

    def __init__(self, planar, faces, cycle, steps, failure=None,
                 embedded_edges=None):
        self.planar = planar
        self.faces = faces
        self.cycle = cycle
        self.steps = steps
        self.failure = failure              # мост, которому не нашлось грани
        self.embedded_edges = embedded_edges or set()


def _adjacency(edges):
    adj = {}
    for u, v in edges:
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)
    return adj


def find_cycle(adj):
    """Найти простой цикл обходом в глубину.

    В обходе неориентированного графа в глубину любое непройденное ребро,
    ведущее в уже посещённую вершину, ведёт к предку, и вместе с путём по
    дереву поиска оно замыкает цикл.
    """
    start = min(adj)
    path = [start]
    position = {start: 0}
    stack = [iter(sorted(adj[start]))]
    visited = {start}

    while stack:
        vertex = path[-1]
        parent = path[-2] if len(path) > 1 else None
        advanced = False
        for neighbor in stack[-1]:
            if neighbor == parent:
                continue
            if neighbor in position:
                return path[position[neighbor]:]
            if neighbor not in visited:
                visited.add(neighbor)
                position[neighbor] = len(path)
                path.append(neighbor)
                stack.append(iter(sorted(adj[neighbor])))
                advanced = True
                break
        if not advanced:
            stack.pop()
            del position[path.pop()]
    raise ValueError("в графе нет циклов")


def find_bridges(adj, embedded_vertices, embedded_edges):
    """Все мосты относительно уложенного подграфа H."""
    bridges = []

    for u in sorted(adj):
        for v in sorted(adj[u]):
            if u < v and u in embedded_vertices and v in embedded_vertices:
                if (u, v) not in embedded_edges:
                    bridges.append(Bridge({(u, v)}, set(), {u, v}))

    seen = set()
    for start in sorted(adj):
        if start in embedded_vertices or start in seen:
            continue
        component = {start}
        seen.add(start)
        queue = deque([start])
        while queue:
            vertex = queue.popleft()
            for neighbor in adj[vertex]:
                if neighbor not in embedded_vertices and neighbor not in seen:
                    seen.add(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        contacts = {w for x in component for w in adj[x] if w in embedded_vertices}
        edges = {edge_key(x, w) for x in component for w in adj[x]}
        bridges.append(Bridge(edges, component, contacts))

    return bridges


def bridge_path(adj, bridge):
    """Цепь внутри моста между двумя его контактными вершинами."""
    contacts = sorted(bridge.contacts)
    a, b = contacts[0], contacts[1]
    if not bridge.inner:
        return [a, b]

    # Обход в ширину по внутренним вершинам моста: от соседей a до
    # вершины, смежной с b.
    parent = {}
    queue = deque()
    for x in sorted(adj[a]):
        if x in bridge.inner:
            parent[x] = a
            queue.append(x)
    while queue:
        x = queue.popleft()
        if b in adj[x]:
            chain = [x]
            while parent[chain[-1]] != a:
                chain.append(parent[chain[-1]])
            return [a] + list(reversed(chain)) + [b]
        for y in sorted(adj[x]):
            if y in bridge.inner and y not in parent:
                parent[y] = x
                queue.append(y)
    raise AssertionError("мост несвязен — так быть не может")


def split_face(face, path):
    """Разбить грань цепью path, соединяющей две вершины её границы.

    Грань face = (a, ..., b, ...) после поворота. Цепь a → p1 → … → pr → b
    делит её на две: a → … → b → pr → … → p1 и b → … → a → p1 → … → pr.
    Каждое ребро цепи входит в новые грани в противоположных направлениях,
    так что согласованная ориентация сохраняется.
    """
    a, b = path[0], path[-1]
    inner = path[1:-1]
    shift = face.index(a)
    rotated = face[shift:] + face[:shift]
    t = rotated.index(b)
    first = rotated[:t + 1] + list(reversed(inner))
    second = rotated[t:] + [a] + inner
    return first, second


def embed_block(edges):
    """Проверить планарность двусвязного блока и построить его укладку."""
    adj = _adjacency(edges)
    all_edges = {edge_key(u, v) for u, v in edges}

    cycle = find_cycle(adj)
    embedded_vertices = set(cycle)
    embedded_edges = {
        edge_key(cycle[i], cycle[(i + 1) % len(cycle)]) for i in range(len(cycle))
    }
    faces = [list(cycle), list(reversed(cycle))]
    steps = []

    while len(embedded_edges) < len(all_edges):
        options = []
        for bridge in find_bridges(adj, embedded_vertices, embedded_edges):
            fits = [i for i, face in enumerate(faces) if bridge.contacts <= set(face)]
            if not fits:
                return BlockEmbedding(
                    False, faces, cycle, steps, failure=bridge,
                    embedded_edges=set(embedded_edges),
                )
            options.append((bridge, fits))

        # Мост с единственной подходящей гранью берётся в первую очередь.
        bridge, fits = min(options, key=lambda option: len(option[1]))
        face_index = fits[0]
        path = bridge_path(adj, bridge)
        steps.append(Step(bridge, len(fits), list(faces[face_index]), path))

        first, second = split_face(faces[face_index], path)
        faces[face_index:face_index + 1] = [first, second]
        embedded_vertices.update(path)
        embedded_edges.update(edge_key(path[i], path[i + 1]) for i in range(len(path) - 1))

    return BlockEmbedding(True, faces, cycle, steps, embedded_edges=embedded_edges)
