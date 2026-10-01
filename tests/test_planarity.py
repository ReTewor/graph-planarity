import itertools
import random
import unittest

from graphplanar import Graph, check_planarity, drawing_defects, face_walk, tutte_layout
from graphplanar.blocks import biconnected_components, connected_components
from graphplanar.demos import (BLOCKS, CUBE, K33_SUBDIVIDED, OCTAHEDRON, PETERSEN,
                               PRACTICE, PRISM, complete, complete_bipartite, cycle,
                               grid, wheel)
from graphplanar.demoucron import embed_block, find_cycle, split_face
from graphplanar.embedding import faces_per_component, make_biconnected
from graphplanar.geometry import segments_intersect

try:
    import networkx
except ImportError:          # сверка с NetworkX необязательна
    networkx = None


def make(edges, vertices=()):
    graph = Graph()
    for v in vertices:
        graph.add_vertex(v)
    for u, v in edges:
        graph.add_edge(u, v)
    return graph


def random_graph(n, p, rng):
    edges = [(u, v) for u, v in itertools.combinations(range(1, n + 1), 2) if rng.random() < p]
    return make(edges, range(1, n + 1))


def triangulated_grid(rows, cols):
    def vid(r, c):
        return r * cols + c + 1
    return grid(rows, cols) + [(vid(r, c), vid(r + 1, c + 1))
                               for r in range(rows - 1) for c in range(cols - 1)]


PLANAR = {
    "K4": complete(4),
    "куб": CUBE,
    "октаэдр": OCTAHEDRON,
    "призма": PRISM,
    "колесо": wheel(7),
    "решётка": grid(4, 4),
    "цикл": cycle(9),
    "K2,5": complete_bipartite(2, 5),
    "граф 8а": PRACTICE,
    "блоки": BLOCKS,
}

NONPLANAR = {
    "K5": complete(5),
    "K3,3": complete_bipartite(3, 3),
    "K6": complete(6),
    "Петерсен": PETERSEN,
    "подразделение K3,3": K33_SUBDIVIDED,
    "K3,3 с хвостом": complete_bipartite(3, 3) + [(6, 7), (7, 8)],
}


class TestBlocks(unittest.TestCase):
    def test_blocks_and_cut_vertices(self):
        blocks, cuts = biconnected_components(make(BLOCKS))
        self.assertEqual(cuts, {1, 3, 5, 9, 13})
        sizes = sorted(len(block) for block in blocks)
        self.assertEqual(sizes, [1, 1, 1, 3, 3, 3, 4])

    def test_connected_components(self):
        graph = make([(1, 2), (3, 4)], vertices=[5])
        self.assertEqual(connected_components(graph), [[1, 2], [3, 4], [5]])

    def test_biconnected_graph_has_one_block(self):
        blocks, cuts = biconnected_components(make(CUBE))
        self.assertEqual(len(blocks), 1)
        self.assertEqual(cuts, set())


class TestDemoucron(unittest.TestCase):
    def test_find_cycle_is_a_cycle(self):
        adj = {}
        for u, v in CUBE:
            adj.setdefault(u, set()).add(v)
            adj.setdefault(v, set()).add(u)
        found = find_cycle(adj)
        self.assertGreaterEqual(len(found), 3)
        for i in range(len(found)):
            self.assertIn(found[(i + 1) % len(found)], adj[found[i]])

    def test_split_face_keeps_orientation(self):
        first, second = split_face([1, 2, 3, 4, 5, 6], [2, 7, 5])
        self.assertEqual(first, [2, 3, 4, 5, 7])
        self.assertEqual(second, [5, 6, 1, 2, 7])

    def test_faces_satisfy_euler(self):
        embedding = embed_block(CUBE)
        self.assertTrue(embedding.planar)
        self.assertEqual(8 - 12 + len(embedding.faces), 2)

    def test_every_edge_in_two_faces_in_opposite_directions(self):
        embedding = embed_block(OCTAHEDRON)
        darts = [(f[i], f[(i + 1) % len(f)]) for f in embedding.faces for i in range(len(f))]
        self.assertEqual(len(darts), len(set(darts)))
        self.assertEqual(len(darts), 2 * len(OCTAHEDRON))
        for a, b in darts:
            self.assertIn((b, a), darts)

    def test_failure_bridge_fits_no_face(self):
        embedding = embed_block(complete(5))
        self.assertFalse(embedding.planar)
        for face in embedding.faces:
            self.assertFalse(embedding.failure.contacts <= set(face))


class TestPlanarity(unittest.TestCase):
    def test_known_planar(self):
        for name, edges in PLANAR.items():
            with self.subTest(name):
                self.assertTrue(check_planarity(make(edges)).planar)

    def test_known_nonplanar(self):
        for name, edges in NONPLANAR.items():
            with self.subTest(name):
                self.assertFalse(check_planarity(make(edges)).planar)

    def test_trivial_graphs(self):
        for graph in (make([]), make([], vertices=[1]), make([(1, 2)])):
            self.assertTrue(check_planarity(graph).planar)

    def test_euler_formula_per_component(self):
        for name, edges in PLANAR.items():
            with self.subTest(name):
                result = check_planarity(make(edges))
                for component, m, f in faces_per_component(result):
                    self.assertEqual(len(component) - m + f, 2)

    def test_rotation_lists_every_neighbour_once(self):
        graph = make(BLOCKS)
        result = check_planarity(graph)
        for v in graph.vertices:
            self.assertEqual(sorted(result.rotation[v]), graph.neighbors(v))

    @unittest.skipIf(networkx is None, "NetworkX не установлен")
    def test_matches_networkx_on_random_graphs(self):
        rng = random.Random(20260925)
        for _ in range(400):
            graph = random_graph(rng.randint(1, 11), rng.uniform(0.1, 0.7), rng)
            reference = networkx.Graph()
            reference.add_nodes_from(graph.vertices)
            reference.add_edges_from(graph.edges)
            expected, _ = networkx.check_planarity(reference)
            self.assertEqual(check_planarity(graph).planar, expected, graph.edges)


class TestMakeBiconnected(unittest.TestCase):
    def test_tree_becomes_biconnected(self):
        graph = make([(1, 2), (1, 3), (1, 4), (4, 5), (4, 6)])
        result = check_planarity(graph)
        augmented, rotation, added = make_biconnected(graph, result.rotation)
        _, cuts = biconnected_components(augmented)
        self.assertEqual(cuts, set())
        self.assertTrue(check_planarity(augmented).planar)
        faces = face_walk(rotation)
        self.assertEqual(augmented.order() - augmented.size() + len(faces), 2)
        for u, v in graph.edges:
            self.assertIn(v, augmented.neighbors(u))


class TestGeometry(unittest.TestCase):
    def test_checker_finds_real_problems(self):
        self.assertTrue(segments_intersect((0, 0), (1, 1), (0, 1), (1, 0)))
        self.assertTrue(segments_intersect((0, 0), (2, 0), (1, 0), (1, 1)))
        self.assertFalse(segments_intersect((0, 0), (1, 0), (0, 1), (1, 1)))
        self.assertTrue(drawing_defects({1: (0, 0), 2: (2, 0), 3: (1, 0)}, [(1, 2)]))
        tiny = {1: (0, 0), 2: (1e-6, 1e-6), 3: (0, 1e-6), 4: (1e-6, 0)}
        self.assertTrue(drawing_defects(tiny, [(1, 2), (3, 4)]))

    def draw(self, graph, relax=True):
        result = check_planarity(graph)
        positions, _ = tutte_layout(graph, result.rotation, result.components, relax)
        return positions

    def test_demo_drawings_are_plane(self):
        for name, edges in PLANAR.items():
            for relax in (False, True):
                with self.subTest(name, relax=relax):
                    graph = make(edges)
                    self.assertEqual(drawing_defects(self.draw(graph, relax), graph.edges), [])

    def test_random_planar_drawings_are_plane(self):
        rng = random.Random(7)
        for _ in range(40):
            edges = [e for e in triangulated_grid(rng.randint(2, 5), rng.randint(2, 5))
                     if rng.random() < rng.uniform(0.4, 1.0)]
            if not edges:
                continue
            graph = make(edges)
            self.assertEqual(drawing_defects(self.draw(graph), graph.edges), [], graph.edges)

    def test_isolated_vertices_are_drawn(self):
        graph = make([(1, 2)], vertices=[3, 4])
        positions = self.draw(graph)
        self.assertEqual(set(positions), {1, 2, 3, 4})
        self.assertEqual(drawing_defects(positions, graph.edges), [])


if __name__ == "__main__":
    unittest.main()
