from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

from semantica.explorer.session import GraphSession

DEFAULT_GRAPH = Path(r".\demo_out_100k\primekg_demo_graph.json")
DEFAULT_QUERIES = [
    "metformin",
    "metf",
    "AICA ribonucleotide",
    "drug:DB06736",
    "protein",
    "glucophagezz",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark GraphSession.search() against a local explorer graph JSON.",
    )
    parser.add_argument(
        "--graph",
        default=str(DEFAULT_GRAPH),
        help=f"Path to graph JSON (default: {DEFAULT_GRAPH})",
    )
    parser.add_argument(
        "--query",
        dest="queries",
        action="append",
        help="Query to benchmark. Repeat the flag to add multiple queries.",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=80,
        help="Total search calls per query, including warmup (default: 80)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=10,
        help="How many initial calls to exclude from warm metrics (default: 10)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=8,
        help="Search result limit to pass to GraphSession.search() (default: 8)",
    )
    return parser.parse_args()


def format_ms(value: float) -> str:
    return f"{value:8.3f}"


def main() -> None:
    args = parse_args()
    graph_path = Path(args.graph).expanduser().resolve()
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph JSON not found: {graph_path}")

    queries = args.queries or list(DEFAULT_QUERIES)
    warmup = max(0, min(args.warmup, args.rounds - 1))

    print(f"Loading graph: {graph_path}")
    load_started = time.perf_counter()
    session = GraphSession.from_file(str(graph_path))
    load_ms = (time.perf_counter() - load_started) * 1000

    stats = session.get_stats()
    print(
        f"Loaded {stats.get('node_count', 0):,} nodes / {stats.get('edge_count', 0):,} edges "
        f"in {load_ms:.1f} ms"
    )
    print(
        f"Rounds per query: {args.rounds} (warmup excluded from warm stats: {warmup}) | limit={args.limit}"
    )
    print("")

    header = (
        f"{'query':24} {'cold':>8} {'warm_med':>10} {'warm_min':>10} "
        f"{'warm_max':>10} {'warm_avg':>10}"
    )
    print(header)
    print("-" * len(header))

    for query in queries:
        timings: list[float] = []
        for _ in range(args.rounds):
            started = time.perf_counter()
            session.search(query, args.limit, {})
            timings.append((time.perf_counter() - started) * 1000)

        cold = timings[0]
        warm = timings[warmup:] if warmup < len(timings) else timings

        print(
            f"{query[:24]:24} "
            f"{format_ms(cold)} "
            f"{format_ms(statistics.median(warm))} "
            f"{format_ms(min(warm))} "
            f"{format_ms(max(warm))} "
            f"{format_ms(statistics.fmean(warm))}"
        )


if __name__ == "__main__":
    main()
