"""Компоненты связности и блоки (компоненты двусвязности).

Алгоритм Демукрона работает только с двусвязными графами, поэтому
произвольный граф сначала разбивается на части: граф планарен тогда и
только тогда, когда планарен каждый его блок.
"""

from collections import deque


def edge_key(u, v):
    """Ребро как упорядоченная пара, чтобы [u, v] и [v, u] совпадали."""
    return (u, v) if u <= v else (v, u)


def connected_components(graph):
    """Список компонент связности, каждая — отсортированный список вершин."""
    seen = set()
    components = []
    for start in graph.vertices:
        if start in seen:
            continue
        seen.add(start)
        queue = deque([start])
        component = []
        while queue:
            vertex = queue.popleft()
            component.append(vertex)
            for neighbor in graph.neighbors(vertex):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    return components


def biconnected_components(graph):
    """Блоки графа и его точки сочленения (алгоритм Хопкрофта — Тарьяна).

    Возвращает (blocks, cut_vertices), где blocks — список блоков, каждый
    блок — список рёбер. Мост образует блок из одного ребра. Изолированные
    вершины блоков не образуют.

    Обход в глубину итеративный, чтобы длинные цепи не упирались в предел
    рекурсии. Для каждой вершины считаются время входа disc и величина low —
    наименьшее время входа, достижимое из поддерева по одному обратному
    ребру. Если у потомка w вершины v выполняется low[w] >= disc[v], то
    рёбра поддерева w вместе с ребром [v, w] образуют блок.
    """
    disc = {}
    low = {}
    clock = 0
    blocks = []
    cut_vertices = set()

    for root in graph.vertices:
        if root in disc:
            continue
        disc[root] = low[root] = clock
        clock += 1
        root_children = 0
        edge_stack = []
        stack = [(root, None, iter(graph.neighbors(root)))]

        while stack:
            vertex, parent, neighbors = stack[-1]
            descended = False
            for neighbor in neighbors:
                if neighbor == parent:
                    continue
                if neighbor not in disc:
                    edge_stack.append((vertex, neighbor))
                    disc[neighbor] = low[neighbor] = clock
                    clock += 1
                    if vertex == root:
                        root_children += 1
                    stack.append((neighbor, vertex, iter(graph.neighbors(neighbor))))
                    descended = True
                    break
                if disc[neighbor] < disc[vertex]:
                    # обратное ребро к предку
                    edge_stack.append((vertex, neighbor))
                    low[vertex] = min(low[vertex], disc[neighbor])
            if descended:
                continue

            stack.pop()
            if parent is None:
                continue
            low[parent] = min(low[parent], low[vertex])
            if low[vertex] >= disc[parent]:
                if parent != root:
                    cut_vertices.add(parent)
                block = []
                while True:
                    edge = edge_stack.pop()
                    block.append(edge_key(*edge))
                    if edge == (parent, vertex):
                        break
                blocks.append(sorted(block))

        if root_children > 1:
            cut_vertices.add(root)

    return blocks, cut_vertices


def block_vertices(block):
    """Вершины блока, заданного списком рёбер."""
    return sorted({v for edge in block for v in edge})
