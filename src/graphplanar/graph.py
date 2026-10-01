"""Неориентированный граф на списках смежности."""

from collections import deque


class Graph:
    """Простой неориентированный граф без петель и кратных рёбер.

    Вершины — произвольные хешируемые объекты, в этом проекте целые числа.
    Рёбра могут иметь вес; если вес не задан, он равен None.
    """

    def __init__(self):
        self._adj = {}
        self._weights = {}

    # ------------------------------------------------------------------
    # построение
    # ------------------------------------------------------------------

    def add_vertex(self, v):
        """Добавить вершину. Повторное добавление ничего не меняет."""
        self._adj.setdefault(v, set())

    def add_edge(self, u, v, weight=None):
        """Добавить ребро. Вершины создаются автоматически."""
        if u == v:
            raise ValueError(f"петля недопустима: вершина {u}")
        self.add_vertex(u)
        self.add_vertex(v)
        self._adj[u].add(v)
        self._adj[v].add(u)
        self._weights[self._key(u, v)] = weight

    # ------------------------------------------------------------------
    # доступ
    # ------------------------------------------------------------------

    @staticmethod
    def _key(u, v):
        return (u, v) if u <= v else (v, u)

    @property
    def vertices(self):
        """Вершины в отсортированном порядке."""
        return sorted(self._adj)

    @property
    def edges(self):
        """Рёбра как список пар (u, v), u < v, в отсортированном порядке."""
        return sorted(self._weights)

    def weight(self, u, v):
        return self._weights[self._key(u, v)]

    def neighbors(self, v):
        """Соседи вершины в отсортированном порядке."""
        return sorted(self._adj[v])

    def degree(self, v):
        return len(self._adj[v])

    def order(self):
        """Число вершин n."""
        return len(self._adj)

    def size(self):
        """Число рёбер m."""
        return len(self._weights)

    # ------------------------------------------------------------------
    # свойства
    # ------------------------------------------------------------------

    def distances_from(self, start):
        """Расстояния в рёбрах от start до всех достижимых вершин (обход в ширину)."""
        dist = {start: 0}
        queue = deque([start])
        while queue:
            v = queue.popleft()
            for u in self.neighbors(v):
                if u not in dist:
                    dist[u] = dist[v] + 1
                    queue.append(u)
        return dist

    def is_connected(self):
        if not self._adj:
            return True
        start = next(iter(self._adj))
        return len(self.distances_from(start)) == self.order()

    def is_tree(self):
        """Дерево — связный граф, в котором ровно n - 1 ребро."""
        return self.is_connected() and self.size() == self.order() - 1

    def leaves(self):
        """Концевые вершины — степень равна единице."""
        return [v for v in self.vertices if self.degree(v) == 1]

    def eccentricities(self):
        """Удалённость каждой вершины: расстояние до самой дальней."""
        result = {}
        for v in self.vertices:
            dist = self.distances_from(v)
            if len(dist) < self.order():
                raise ValueError("граф несвязен, удалённость не определена")
            result[v] = max(dist.values())
        return result

    def radius(self):
        return min(self.eccentricities().values())

    def diameter(self):
        return max(self.eccentricities().values())

    def center(self):
        """Вершины, удалённость которых равна радиусу."""
        ecc = self.eccentricities()
        r = min(ecc.values())
        return [v for v in self.vertices if ecc[v] == r]

    def __repr__(self):
        return f"Graph(n={self.order()}, m={self.size()})"
