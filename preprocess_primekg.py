from __future__ import annotations

import argparse
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from semantica.context.context_graph import ContextGraph


REQUIRED_COLUMNS = [
    "relation",
    "display_relation",
    "x_id",
    "x_type",
    "x_name",
    "x_source",
    "y_id",
    "y_type",
    "y_name",
    "y_source",
]


@dataclass
class NodeRecord:
    node_id: str
    node_type: str
    content: str
    metadata: dict[str, Any]


@dataclass
class EdgeRecord:
    source: str
    target: str
    edge_type: str
    metadata: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Semantica Explorer demo graph from PrimeKG."
    )
    parser.add_argument("--input", required=True, help="Path to PrimeKG kg.csv")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where demo CSVs and graph JSON will be written",
    )
    parser.add_argument(
        "--anchors",
        nargs="+",
        required=True,
        help="Anchor terms used to seed the neighborhood search",
    )
    parser.add_argument(
        "--hops",
        type=int,
        default=2,
        help="Number of neighborhood expansion hops (default: 2)",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=200_000,
        help="CSV chunk size for streaming reads (default: 200000)",
    )
    parser.add_argument(
        "--max-edges",
        type=int,
        default=50_000,
        help="Maximum number of unique edges to keep (default: 50000)",
    )
    parser.add_argument(
        "--max-nodes",
        type=int,
        default=150_000,
        help="Maximum number of unique nodes to keep before expansion stops (default: 150000)",
    )
    parser.add_argument(
        "--novelty-fanout-per-node",
        type=int,
        default=96,
        help=(
            "Maximum unseen-node edges to keep per frontier node on each hop. "
            "Higher values trade breadth for local density (default: 96)"
        ),
    )
    parser.add_argument(
        "--context-fanout-per-node",
        type=int,
        default=12,
        help=(
            "Maximum already-known context edges to keep per frontier node on each hop "
            "after novelty edges are collected (default: 12)"
        ),
    )
    return parser.parse_args()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    return " ".join(text.split())


def coerce_scalar(value: Any) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if value.is_integer():
            return str(int(value))
    return str(value).strip()


def canonical_node_id(node_type: Any, raw_id: Any) -> str:
    return f"{coerce_scalar(node_type)}:{coerce_scalar(raw_id)}"


def matches_anchor(name: Any, anchor_terms: set[str]) -> bool:
    normalized = normalize_text(name)
    if not normalized:
        return False
    if normalized in anchor_terms:
        return True
    return any(term in normalized for term in anchor_terms)


def chunk_reader(csv_path: Path, chunksize: int):
    return pd.read_csv(
        csv_path,
        usecols=REQUIRED_COLUMNS,
        chunksize=chunksize,
        dtype={column: "string" for column in REQUIRED_COLUMNS},
        keep_default_na=False,
        low_memory=False,
    )


def build_node_record(row: pd.Series, prefix: str) -> NodeRecord:
    node_type = coerce_scalar(row[f"{prefix}_type"])
    raw_id = coerce_scalar(row[f"{prefix}_id"])
    name = coerce_scalar(row[f"{prefix}_name"]) or raw_id
    source = coerce_scalar(row[f"{prefix}_source"])
    node_id = canonical_node_id(node_type, raw_id)
    metadata = {
        "name": name,
        "source_system": source,
        "primekg_id": raw_id,
        "category": node_type,
    }
    return NodeRecord(
        node_id=node_id,
        node_type=node_type or "entity",
        content=name,
        metadata=metadata,
    )


def build_edge_record(row: pd.Series) -> EdgeRecord:
    relation = coerce_scalar(row["relation"]) or "related_to"
    display_relation = coerce_scalar(row["display_relation"]) or relation
    source = canonical_node_id(row["x_type"], row["x_id"])
    target = canonical_node_id(row["y_type"], row["y_id"])
    metadata = {
        "display_relation": display_relation,
        "source_type": coerce_scalar(row["x_type"]),
        "target_type": coerce_scalar(row["y_type"]),
        "source_name": coerce_scalar(row["x_name"]),
        "target_name": coerce_scalar(row["y_name"]),
        "source_system_x": coerce_scalar(row["x_source"]),
        "source_system_y": coerce_scalar(row["y_source"]),
        "weight": 1.0,
    }
    return EdgeRecord(source=source, target=target, edge_type=relation, metadata=metadata)


def find_anchor_nodes(csv_path: Path, anchor_terms: set[str], chunksize: int) -> dict[str, NodeRecord]:
    anchor_nodes: dict[str, NodeRecord] = {}

    for chunk in chunk_reader(csv_path, chunksize):
        for _, row in chunk.iterrows():
            if matches_anchor(row["x_name"], anchor_terms):
                record = build_node_record(row, "x")
                anchor_nodes.setdefault(record.node_id, record)
            if matches_anchor(row["y_name"], anchor_terms):
                record = build_node_record(row, "y")
                anchor_nodes.setdefault(record.node_id, record)

    return anchor_nodes


def expand_neighborhood(
    csv_path: Path,
    seed_nodes: dict[str, NodeRecord],
    hops: int,
    chunksize: int,
    max_edges: int,
    max_nodes: int,
    novelty_fanout_per_node: int,
    context_fanout_per_node: int,
) -> tuple[dict[str, NodeRecord], list[EdgeRecord]]:
    selected_nodes: dict[str, NodeRecord] = dict(seed_nodes)
    selected_edges: dict[tuple[str, str, str], EdgeRecord] = {}

    frontier = set(seed_nodes.keys())
    visited = set(seed_nodes.keys())

    def _frontier_endpoints(source_id: str, target_id: str) -> list[str]:
        endpoints = []
        if source_id in frontier:
            endpoints.append(source_id)
        if target_id in frontier and target_id != source_id:
            endpoints.append(target_id)
        return endpoints

    def _can_accept_edge(
        active_frontier_nodes: list[str],
        counts: dict[str, int],
        limit_per_node: int,
    ) -> bool:
        if not active_frontier_nodes or limit_per_node <= 0:
            return limit_per_node <= 0 and not active_frontier_nodes
        return any(counts[node_id] < limit_per_node for node_id in active_frontier_nodes)

    def _mark_edge_consumed(active_frontier_nodes: list[str], counts: dict[str, int]) -> None:
        for node_id in active_frontier_nodes:
            counts[node_id] += 1

    for hop_index in range(hops):
        if (
            not frontier
            or len(selected_edges) >= max_edges
            or len(selected_nodes) >= max_nodes
        ):
            break

        next_frontier: set[str] = set()
        novelty_counts: dict[str, int] = defaultdict(int)
        context_counts: dict[str, int] = defaultdict(int)
        print(f"Scanning hop {hop_index + 1}/{hops} from {len(frontier)} frontier nodes...")

        start_node_count = len(selected_nodes)
        start_edge_count = len(selected_edges)
        stop = False

        # Pass 1: prioritize edges that introduce at least one unseen node.
        for chunk in chunk_reader(csv_path, chunksize):
            for _, row in chunk.iterrows():
                source_id = canonical_node_id(row["x_type"], row["x_id"])
                target_id = canonical_node_id(row["y_type"], row["y_id"])

                if source_id not in frontier and target_id not in frontier:
                    continue
                if source_id in selected_nodes and target_id in selected_nodes:
                    continue

                active_frontier_nodes = _frontier_endpoints(source_id, target_id)
                if not _can_accept_edge(
                    active_frontier_nodes,
                    novelty_counts,
                    novelty_fanout_per_node,
                ):
                    continue

                new_node_ids = [node_id for node_id in (source_id, target_id) if node_id not in selected_nodes]
                if new_node_ids and len(selected_nodes) + len(new_node_ids) > max_nodes:
                    stop = True
                    break

                edge_record = build_edge_record(row)
                edge_key = (edge_record.source, edge_record.target, edge_record.edge_type)
                if edge_key in selected_edges:
                    continue

                source_record = build_node_record(row, "x")
                target_record = build_node_record(row, "y")
                selected_nodes.setdefault(source_record.node_id, source_record)
                selected_nodes.setdefault(target_record.node_id, target_record)

                selected_edges[edge_key] = edge_record
                _mark_edge_consumed(active_frontier_nodes, novelty_counts)
                if len(selected_edges) >= max_edges or len(selected_nodes) >= max_nodes:
                    stop = True

                if source_id not in visited:
                    next_frontier.add(source_id)
                if target_id not in visited:
                    next_frontier.add(target_id)

                if stop:
                    break
            if stop:
                break

        # Pass 2: add a small amount of context among already-selected nodes so the
        # extracted graph doesn't look amputated, but keep this secondary to novelty.
        if (
            not stop
            and context_fanout_per_node > 0
            and len(selected_edges) < max_edges
        ):
            for chunk in chunk_reader(csv_path, chunksize):
                for _, row in chunk.iterrows():
                    source_id = canonical_node_id(row["x_type"], row["x_id"])
                    target_id = canonical_node_id(row["y_type"], row["y_id"])

                    if source_id not in frontier and target_id not in frontier:
                        continue
                    if source_id not in selected_nodes or target_id not in selected_nodes:
                        continue

                    edge_record = build_edge_record(row)
                    edge_key = (edge_record.source, edge_record.target, edge_record.edge_type)
                    if edge_key in selected_edges:
                        continue

                    active_frontier_nodes = _frontier_endpoints(source_id, target_id)
                    if not _can_accept_edge(
                        active_frontier_nodes,
                        context_counts,
                        context_fanout_per_node,
                    ):
                        continue

                    selected_edges[edge_key] = edge_record
                    _mark_edge_consumed(active_frontier_nodes, context_counts)
                    if len(selected_edges) >= max_edges:
                        stop = True
                        break
                if stop:
                    break

        next_frontier -= visited
        visited |= next_frontier
        frontier = next_frontier
        print(
            f"  Added {len(selected_nodes) - start_node_count:,} node(s) and "
            f"{len(selected_edges) - start_edge_count:,} edge(s) on this hop."
        )

    return selected_nodes, list(selected_edges.values())


def write_csvs(output_dir: Path, nodes: dict[str, NodeRecord], edges: list[EdgeRecord]) -> None:
    node_rows = []
    for node in nodes.values():
        node_rows.append(
            {
                "id": node.node_id,
                "name": node.content,
                "type": node.node_type,
                "source_system": node.metadata.get("source_system", ""),
                "primekg_id": node.metadata.get("primekg_id", ""),
            }
        )

    edge_rows = []
    for edge in edges:
        edge_rows.append(
            {
                "source": edge.source,
                "target": edge.target,
                "type": edge.edge_type,
                "display_relation": edge.metadata.get("display_relation", edge.edge_type),
                "source_name": edge.metadata.get("source_name", ""),
                "target_name": edge.metadata.get("target_name", ""),
            }
        )

    pd.DataFrame(node_rows).sort_values(["type", "name", "id"]).to_csv(
        output_dir / "primekg_demo_nodes.csv", index=False
    )
    pd.DataFrame(edge_rows).to_csv(output_dir / "primekg_demo_edges.csv", index=False)


def write_graph_json(output_dir: Path, nodes: dict[str, NodeRecord], edges: list[EdgeRecord]) -> Path:
    graph = ContextGraph()

    graph.add_nodes(
        [
            {
                "id": node.node_id,
                "type": node.node_type,
                "content": node.content,
                "properties": node.metadata,
            }
            for node in nodes.values()
        ]
    )

    graph.add_edges(
        [
            {
                "source": edge.source,
                "target": edge.target,
                "type": edge.edge_type,
                "weight": 1.0,
                "properties": edge.metadata,
            }
            for edge in edges
        ]
    )

    graph_path = output_dir / "primekg_demo_graph.json"
    graph.save_to_file(str(graph_path))
    return graph_path


def main() -> None:
    args = parse_args()
    csv_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    anchor_terms = {normalize_text(term) for term in args.anchors if normalize_text(term)}
    if not anchor_terms:
        raise ValueError("At least one non-empty anchor term is required.")

    print(f"Loading anchors from {csv_path} ...")
    seed_nodes = find_anchor_nodes(csv_path, anchor_terms, args.chunksize)
    if not seed_nodes:
        raise RuntimeError(
            "No anchor nodes matched the provided terms. Check the anchor spellings against kg.csv."
        )

    print(f"Matched {len(seed_nodes)} anchor node(s).")
    nodes, edges = expand_neighborhood(
        csv_path=csv_path,
        seed_nodes=seed_nodes,
        hops=args.hops,
        chunksize=args.chunksize,
        max_edges=args.max_edges,
        max_nodes=args.max_nodes,
        novelty_fanout_per_node=args.novelty_fanout_per_node,
        context_fanout_per_node=args.context_fanout_per_node,
    )

    write_csvs(output_dir, nodes, edges)
    graph_path = write_graph_json(output_dir, nodes, edges)

    print("")
    print("PrimeKG demo graph ready.")
    print(f"Nodes: {len(nodes):,}")
    print(f"Edges: {len(edges):,}")
    print(f"Output directory: {output_dir}")
    print(f"Graph JSON: {graph_path}")
    print("")
    print(
        f"Next: python -m semantica.explorer --graph {graph_path} --host 127.0.0.1 --port 8000 --no-browser"
    )


if __name__ == "__main__":
    main()
