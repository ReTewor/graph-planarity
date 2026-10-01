"""Командный интерфейс.

    python -m graphplanar --demo practice --svg ../examples/practice.svg
    python -m graphplanar --edges graph.json --svg out.svg --dot out.dot
    python -m graphplanar --list-demos
"""

import argparse
import json
import sys

from . import dot, render
from .blocks import block_vertices
from .demos import DEMOS
from .embedding import check_planarity, faces_per_component
from .geometry import drawing_defects
from .graph import Graph
from .tutte import tutte_layout


def load_graph(path):
    """Граф из JSON: список рёбер [[1,2],…] или {"vertices": […], "edges": […]}."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    vertices, edges = [], data
    if isinstance(data, dict):
        vertices, edges = data.get("vertices", []), data["edges"]
    graph = Graph()
    for v in vertices:
        graph.add_vertex(v)
    for u, v, *_ in edges:
        graph.add_edge(u, v)
    return graph


def graph_from_edges(edges):
    graph = Graph()
    for u, v in edges:
        graph.add_edge(u, v)
    return graph


def fmt_cycle(vertices):
    return " – ".join(str(v) for v in vertices)


def report_structure(graph, result):
    n, m = graph.order(), graph.size()
    print(f"Граф: n = {n}, m = {m}, компонент связности: {len(result.components)}")
    if n >= 3:
        bound = 3 * n - 6
        verdict = "выполнено" if m <= bound else "НАРУШЕНО — граф заведомо непланарен"
        print(f"Необходимое условие Эйлера m ≤ 3n − 6: {m} ≤ {bound} — {verdict}")
    cycles = [b for b in result.blocks if len(b) > 1]
    print(f"Блоков двусвязности: {len(result.blocks)} "
          f"(с циклами: {len(cycles)}, мостов: {len(result.blocks) - len(cycles)})")
    cuts = ", ".join(str(v) for v in sorted(result.cut_vertices)) or "нет"
    print(f"Точки сочленения: {cuts}")


def report_demoucron(result, show_steps):
    print("\nАлгоритм Демукрона по блокам:")
    number = 0
    for block, embedding in result.block_results:
        if embedding is None:
            continue
        number += 1
        vertices = ", ".join(str(v) for v in block_vertices(block))
        print(f"  блок {number}: вершины {{{vertices}}}, рёбер {len(block)}")
        print(f"    исходный цикл: {fmt_cycle(embedding.cycle)}")
        if show_steps:
            for i, step in enumerate(embedding.steps, 1):
                print(f"    шаг {i}: {step.bridge.describe()}, контактные вершины "
                      f"{sorted(step.bridge.contacts)}, подходящих граней {step.fits}, "
                      f"цепь {fmt_cycle(step.path)}")
        else:
            print(f"    уложено мостов: {len(embedding.steps)}")
        if not embedding.planar:
            bridge = embedding.failure
            print(f"    НЕ УДАЛОСЬ: {bridge.describe()} с контактными вершинами "
                  f"{sorted(bridge.contacts)}")
            print("    не помещается ни в одну грань текущей укладки:")
            for face in embedding.faces:
                print(f"      ({fmt_cycle(face)})")


def report_embedding(graph, result):
    print("\nКомбинаторная укладка — система вращений (соседи в циклическом порядке):")
    for v in graph.vertices:
        neighbours = " ".join(str(u) for u in result.rotation[v]) or "—"
        print(f"  {v}: {neighbours}")
    print(f"\nГрани (f = {len(result.faces)}):")
    for i, face in enumerate(result.faces, 1):
        print(f"  {i}: ({fmt_cycle(face)})")
    for component, edges, faces in faces_per_component(result):
        n = len(component)
        print(f"Формула Эйлера для компоненты {{{component[0]}…}}: "
              f"n − m + f = {n} − {edges} + {faces} = {n - edges + faces}")


def draw_planar(graph, result, args, title):
    positions, info = tutte_layout(graph, result.rotation, result.components,
                                   relax_enabled=not args.tutte_only)
    defects = drawing_defects(positions, graph.edges)

    print("\nГеометрическая укладка — алгоритм Тутте:")
    print(f"  рёбер добавлено для двусвязности: {len(info.added_edges)}"
          + (f" {info.added_edges}" if info.added_edges else ""))
    print(f"  вспомогательных вершин в гранях: {info.dummy_vertices}")
    for face in info.outer_faces:
        print(f"  внешняя грань: ({fmt_cycle(face)})")
    if info.relax_skipped:
        print("  раздвигание пропущено: в компоненте больше 40 вершин")
    elif not args.tutte_only:
        print(f"  раздвигание с сохранением планарности: принято перемещений {info.relax_moves}")
    print(f"  проверка рисунка: {'пересечений нет' if not defects else '; '.join(defects)}")

    pixels = render.fit_positions(positions)
    caption = [f"n = {graph.order()}, m = {graph.size()}, граней f = {len(result.faces)}, "
               f"проверка: {'пересечений нет' if not defects else 'есть дефекты'}"]
    if args.svg:
        render.write_svg(args.svg, graph, pixels, title=title, caption_lines=caption)
        print(f"\nSVG записан: {args.svg}")
    if args.dot:
        dot.write_dot(args.dot, graph, pixels, name="planar")
        print(f"DOT записан: {args.dot}")
    return 0 if not defects else 2


def draw_nonplanar(graph, result, args, title):
    block, embedding = result.failure
    bridge = embedding.failure
    edge_style = {edge: "pending" for edge in graph.edges}
    for edge in embedding.embedded_edges:
        edge_style[edge] = "embedded"
    for edge in bridge.edges:
        edge_style[edge] = "conflict"
    vertex_style = {}
    for edge in embedding.embedded_edges:
        for v in edge:
            vertex_style[v] = "embedded"
    for v in bridge.contacts:
        vertex_style[v] = "conflict"

    pixels = render.circular_positions(graph.vertices)
    legend = [
        ("embedded", "уже уложенная часть блока"),
        ("conflict", f"мост {bridge.describe()} — не помещается ни в одну грань"),
        ("pending", "остальные рёбра"),
    ]
    if args.svg:
        render.write_svg(args.svg, graph, pixels, edge_style=edge_style,
                         vertex_style=vertex_style, title=title, legend=legend)
        print(f"\nSVG записан: {args.svg}")
    if args.dot:
        dot.write_dot(args.dot, graph, pixels, edge_style=edge_style, name="nonplanar")
        print(f"DOT записан: {args.dot}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="graphplanar",
        description="Проверка планарности алгоритмом Демукрона и "
                    "плоский рисунок алгоритмом Тутте.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--edges", metavar="FILE", help="граф из JSON-файла")
    source.add_argument("--demo", choices=sorted(DEMOS), help="готовый пример")
    source.add_argument("--list-demos", action="store_true", help="список примеров")
    parser.add_argument("--svg", metavar="FILE", help="записать рисунок")
    parser.add_argument("--dot", metavar="FILE", help="записать DOT-файл")
    parser.add_argument("--steps", action="store_true",
                        help="показать каждый шаг алгоритма Демукрона")
    parser.add_argument("--tutte-only", action="store_true",
                        help="рисунок Тутте без последующего раздвигания вершин")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.list_demos:
        for name in sorted(DEMOS):
            print(f"  {name:10} {DEMOS[name][0]}")
        return 0

    try:
        if args.edges:
            graph = load_graph(args.edges)
            label = args.edges
        else:
            label, edges = DEMOS[args.demo]
            graph = graph_from_edges(edges)
    except (OSError, ValueError, KeyError) as error:
        print(f"Ошибка чтения графа: {error}", file=sys.stderr)
        return 3

    result = check_planarity(graph)
    report_structure(graph, result)
    report_demoucron(result, args.steps)

    if result.planar:
        print("\nРезультат: граф ПЛАНАРЕН")
        report_embedding(graph, result)
        return draw_planar(graph, result, args, f"Плоская укладка: {label}")

    print("\nРезультат: граф НЕПЛАНАРЕН")
    return draw_nonplanar(graph, result, args, f"Граф непланарен: {label}")


if __name__ == "__main__":
    raise SystemExit(main())
