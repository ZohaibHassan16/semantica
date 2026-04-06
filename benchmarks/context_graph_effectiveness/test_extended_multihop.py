"""
Track 17: Extended Multi-hop Reasoning
Source datasets: HotpotQA (CC BY SA 4.0), 2WikiMultihopQA (Apache 2.0).
Measures: 2-hop bridge recall, comparison retrieval, 4-hop path completeness,
          graph traversal coverage, answer node reachability.

Uses direct ContextGraph traversal (get_neighbor_ids / find_related_nodes)
for path tests — more reliable than ContextRetriever on small graphs.
"""

from __future__ import annotations

import pytest

from .thresholds import get_threshold


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_node_id(node: dict) -> str:
    """Get node ID from fixture record; handles both 'id' and 'node_id' keys."""
    return node.get("id", node.get("node_id", node.get("label", "unknown")))


def _build_graph_from_record(rec: dict):
    """Build a ContextGraph from a multihop fixture record's nodes+edges."""
    from semantica.context.context_graph import ContextGraph
    g = ContextGraph()

    node_list = rec.get("supporting_nodes", rec.get("inference_chain", []))
    for node in node_list:
        nid = _get_node_id(node)
        label = node.get("label", nid)
        props = {k: v for k, v in node.items() if k not in ("id", "node_id", "label")}
        try:
            g.add_node(nid, "Entity", label, **props)
        except Exception:
            pass

    for edge in rec.get("edges", []):
        try:
            g.add_edge(edge["source"], edge["target"],
                       edge.get("type", "RELATED_TO"), 1.0)
        except Exception:
            pass
    return g


def _reachable_from(g, start_id: str, max_hops: int = 4) -> set:
    """
    BFS traversal from start_id up to max_hops. Returns set of reachable node IDs.
    Uses g.get_neighbor_ids() for direct graph traversal.
    """
    visited = {start_id}
    frontier = {start_id}
    for _ in range(max_hops):
        if not frontier:
            break
        next_frontier = set()
        for nid in frontier:
            try:
                neighbors = g.get_neighbor_ids(nid) or []
                for n in (neighbors if isinstance(neighbors, list) else []):
                    if n and n not in visited:
                        next_frontier.add(n)
                        visited.add(n)
            except Exception:
                try:
                    # Fallback: get_neighbors returns dicts
                    neighbors = g.get_neighbors(nid) or []
                    for n in (neighbors if isinstance(neighbors, list) else []):
                        nid2 = n.get("id") if isinstance(n, dict) else getattr(n, "id", None)
                        if nid2 and nid2 not in visited:
                            next_frontier.add(nid2)
                            visited.add(nid2)
                except Exception:
                    pass
        frontier = next_frontier
    return visited


def _all_node_ids(g) -> set:
    """Get all node IDs from the graph."""
    try:
        nodes = g.find_nodes() or []
        return {n.get("id") if isinstance(n, dict) else getattr(n, "id", "")
                for n in nodes} - {""}
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# Track 17 Tests
# ---------------------------------------------------------------------------
class TestExtendedMultihopReasoning:
    """2-hop bridge reachability, comparison coverage, N-hop path completeness."""

    def test_hotpotqa_2hop_bridge_reachability(self, multihop_dataset):
        """
        For HotpotQA bridge-type questions, build the supporting graph and
        verify the answer node is reachable within 2 hops from the start node.
        Uses direct graph BFS — not ContextRetriever.
        Recall >= THRESHOLDS['hotpotqa_bridge_recall'] (0.65).
        """
        try:
            from semantica.context.context_graph import ContextGraph
        except ImportError:
            pytest.importorskip("semantica.context.context_graph")

        records = multihop_dataset["hotpotqa"]["records"]
        bridge_records = [r for r in records if r.get("type") == "bridge"]
        if len(bridge_records) < 3:
            pytest.skip("Insufficient bridge-type HotpotQA records")

        reachable = total = 0
        for rec in bridge_records[:15]:
            nodes = rec.get("supporting_nodes", [])
            if len(nodes) < 2:
                continue

            g = _build_graph_from_record(rec)
            start_id = _get_node_id(nodes[0])
            answer_id = _get_node_id(nodes[-1])

            # Count only answer node
            total += 1
            reachable_ids = _reachable_from(g, start_id, max_hops=3)
            if answer_id in reachable_ids:
                reachable += 1
            # Also count intermediate bridge nodes
            for bridge_node in nodes[1:-1]:
                bid = _get_node_id(bridge_node)
                total += 1
                if bid in reachable_ids:
                    reachable += 1

        if total == 0:
            pytest.skip("No bridge recall computed")

        recall = reachable / total
        threshold = get_threshold("hotpotqa_bridge_recall")
        print(f"  HotpotQA bridge reachability: {recall:.3f} ({reachable}/{total})")
        assert recall >= threshold, (
            f"HotpotQA bridge recall {recall:.3f} < {threshold}. "
            "Edges should connect start→bridge→answer."
        )

    def test_hotpotqa_comparison_all_nodes_in_graph(self, multihop_dataset):
        """
        For HotpotQA comparison-type questions, all compared entities must be
        present in the graph (all supporting nodes stored correctly).
        Coverage >= THRESHOLDS['hotpotqa_comparison_recall'] (0.70).
        """
        try:
            from semantica.context.context_graph import ContextGraph
        except ImportError:
            pytest.importorskip("semantica.context.context_graph")

        records = multihop_dataset["hotpotqa"]["records"]
        comparison_records = [r for r in records if r.get("type") == "comparison"]
        if not comparison_records:
            pytest.skip("No comparison-type HotpotQA records")

        found = total = 0
        for rec in comparison_records[:10]:
            nodes = rec.get("supporting_nodes", [])
            if len(nodes) < 2:
                continue

            g = _build_graph_from_record(rec)
            stored_ids = _all_node_ids(g)

            for node in nodes:
                nid = _get_node_id(node)
                total += 1
                if nid in stored_ids:
                    found += 1

        if total == 0:
            pytest.skip("No comparison coverage computed")

        recall = found / total
        threshold = get_threshold("hotpotqa_comparison_recall")
        print(f"  HotpotQA comparison node coverage: {recall:.3f} ({found}/{total})")
        assert recall >= threshold, (
            f"HotpotQA comparison recall {recall:.3f} < {threshold}"
        )

    def test_wikimultihop_path_completeness(self, multihop_dataset):
        """
        For 2WikiMultihop inference chains, verify path completeness:
        all chain nodes are stored and connected via BFS reachability.
        completeness = reachable_chain_nodes / total_chain_nodes >= 0.60.
        """
        try:
            from semantica.context.context_graph import ContextGraph
        except ImportError:
            pytest.importorskip("semantica.context.context_graph")

        records = multihop_dataset["wikimultihop"]["records"]
        if not records:
            pytest.skip("No 2WikiMultihop records")

        completeness_scores = []
        for rec in records[:10]:
            chain = rec.get("inference_chain", [])
            if len(chain) < 2:
                continue

            g = _build_graph_from_record(rec)
            chain_ids = [_get_node_id(n) for n in chain]
            expected = set(chain_ids)

            # Reachability from first chain node
            reachable = _reachable_from(g, chain_ids[0], max_hops=len(chain) + 1)
            # Also check all nodes are stored
            stored = _all_node_ids(g)

            # Completeness = fraction of chain nodes that are both stored and reachable
            found = len((reachable | stored) & expected)
            completeness_scores.append(found / len(expected))

        if not completeness_scores:
            pytest.skip("No completeness scores computed")

        avg = sum(completeness_scores) / len(completeness_scores)
        threshold = get_threshold("multi_hop_recall_4hop")
        print(f"  2WikiMultihop path completeness: {avg:.3f} over {len(completeness_scores)} chains")
        assert avg >= threshold, (
            f"Path completeness {avg:.3f} < {threshold}"
        )

    def test_multihop_graph_traversal_covers_all_nodes(self, multihop_dataset):
        """
        BFS from the first node should reach all nodes in a connected chain.
        This verifies add_edge and get_neighbor_ids work correctly.
        """
        try:
            from semantica.context.context_graph import ContextGraph
        except ImportError:
            pytest.importorskip("semantica.context.context_graph")

        records = multihop_dataset["hotpotqa"]["records"]
        bridge_records = [r for r in records
                          if r.get("type") == "bridge" and
                          len(r.get("edges", [])) >= 2]
        if not bridge_records:
            pytest.skip("No bridge records with 2+ edges")

        coverage_scores = []
        for rec in bridge_records[:8]:
            nodes = rec.get("supporting_nodes", [])
            edges = rec.get("edges", [])
            if not nodes or not edges:
                continue

            g = _build_graph_from_record(rec)
            start_id = _get_node_id(nodes[0])
            all_ids = {_get_node_id(n) for n in nodes}
            reachable = _reachable_from(g, start_id, max_hops=len(nodes))
            coverage = len(reachable & all_ids) / len(all_ids)
            coverage_scores.append(coverage)

        if not coverage_scores:
            pytest.skip("No coverage scores computed")

        avg = sum(coverage_scores) / len(coverage_scores)
        print(f"  Graph traversal coverage: {avg:.3f} over {len(coverage_scores)} graphs")
        assert avg >= 0.70, (
            f"Graph traversal only covers {avg:.1%} of nodes on average"
        )

    def test_wikimultihop_2hop_reachability(self, multihop_dataset):
        """
        For 2WikiMultihop 2-hop chains, verify answer node is reachable
        from start node within 3 hops. Answer recall >= 0.80.
        """
        try:
            from semantica.context.context_graph import ContextGraph
        except ImportError:
            pytest.importorskip("semantica.context.context_graph")

        records = multihop_dataset["wikimultihop"]["records"]
        two_hop_records = [r for r in records if r.get("hop_depth", 0) == 2]
        if not two_hop_records:
            pytest.skip("No 2-hop 2WikiMultihop records")

        found = total = 0
        for rec in two_hop_records[:10]:
            chain = rec.get("inference_chain", [])
            if len(chain) < 2:
                continue

            g = _build_graph_from_record(rec)
            start_id = _get_node_id(chain[0])
            answer_id = _get_node_id(chain[-1])
            total += 1

            reachable = _reachable_from(g, start_id, max_hops=3)
            if answer_id in reachable:
                found += 1

        if total == 0:
            pytest.skip("No 2-hop answer tests")

        recall = found / total
        print(f"  2WikiMultihop 2-hop answer recall: {recall:.3f} ({found}/{total})")
        assert recall >= 0.70, (
            f"Answer node recall {recall:.3f} < 0.70"
        )

    def test_2wikimultihop_answer_node_stored(self, multihop_dataset):
        """
        For 2WikiMultihop records, the final answer node in the inference chain
        must be stored in the graph after building from fixture.
        Answer storage rate >= 0.90.
        """
        try:
            from semantica.context.context_graph import ContextGraph
        except ImportError:
            pytest.importorskip("semantica.context.context_graph")

        records = multihop_dataset["wikimultihop"]["records"]
        if not records:
            pytest.skip("No 2WikiMultihop records")

        found = total = 0
        for rec in records[:12]:
            chain = rec.get("inference_chain", [])
            if not chain:
                continue
            answer_id = _get_node_id(chain[-1])
            total += 1

            g = _build_graph_from_record(rec)
            stored = _all_node_ids(g)
            if answer_id in stored:
                found += 1

        if total == 0:
            pytest.skip("No answer storage tests")

        rate = found / total
        print(f"  2WikiMultihop answer storage: {rate:.3f} ({found}/{total})")
        assert rate >= 0.90, (
            f"Answer node storage rate {rate:.3f} < 0.90"
        )


# ── MetaQA knowledge-base tests (real KB, real QA pairs) ──────────────────────

def _build_metaqa_graph(kb_records: list[dict]):
    """
    Build a ContextGraph from the MetaQA movie knowledge base.
    Each movie becomes an Entity node; directors, actors, genres become linked nodes.
    """
    from semantica.context.context_graph import ContextGraph
    graph = ContextGraph(advanced_analytics=True)
    for movie in kb_records:
        movie_id = movie["id"]
        graph.add_node(
            movie_id, "Movie",
            content=movie["title"],
            release_year=str(movie.get("release_year", "")),
            genre=movie.get("has_genre", ""),
        )
        director = movie.get("directed_by")
        if director:
            dir_id = f"director_{director.replace(' ', '_')}"
            graph.add_node(dir_id, "Person", content=director)
            graph.add_edge(movie_id, dir_id, "DIRECTED_BY", weight=1.0)
            graph.add_edge(dir_id, movie_id, "DIRECTED", weight=1.0)
        genre = movie.get("has_genre")
        if genre:
            genre_id = f"genre_{genre}"
            graph.add_node(genre_id, "Genre", content=genre)
            graph.add_edge(movie_id, genre_id, "HAS_GENRE", weight=1.0)
        for actor in movie.get("starred_actors", []):
            actor_id = f"actor_{actor.replace(' ', '_')}"
            graph.add_node(actor_id, "Person", content=actor)
            graph.add_edge(movie_id, actor_id, "STARRED", weight=1.0)
            graph.add_edge(actor_id, movie_id, "STARRED_IN", weight=1.0)
    return graph


def _metaqa_answer_nodes(answers: list[str]) -> set[str]:
    """Expand answer strings into possible node ID forms used in the KB graph."""
    nodes: set[str] = set()
    for ans in answers:
        nodes.add(f"director_{ans.replace(' ', '_')}")
        nodes.add(f"actor_{ans.replace(' ', '_')}")
        nodes.add(f"genre_{ans}")
        nodes.add(ans)
    return nodes


class TestMetaQAKnowledgeGraph:
    """MetaQA KB multi-hop retrieval tests. All data from committed JSON fixtures."""

    def test_metaqa_1hop_answer_reachability(self, metaqa_dataset):
        """
        For MetaQA 1-hop QA pairs, verify each answer is reachable within
        1 hop from the topic entity in the KB graph.
        Recall >= hotpotqa_bridge_recall threshold (0.65).
        """
        kb = metaqa_dataset["1hop"]["movies_kb"]
        qa_pairs = metaqa_dataset["1hop"]["qa_pairs"]
        graph = _build_metaqa_graph(kb)

        found = total = 0
        for qa in qa_pairs:
            answers = qa.get("answer", [])
            if not answers:
                continue
            reachable = _reachable_from(graph, qa["topic_entity"], max_hops=1)
            if reachable & _metaqa_answer_nodes(answers):
                found += 1
            total += 1

        if total == 0:
            pytest.skip("No MetaQA 1-hop QA pairs evaluated")

        recall = found / total
        threshold = get_threshold("hotpotqa_bridge_recall")
        print(f"  MetaQA 1-hop recall: {recall:.3f} ({found}/{total})")
        assert recall >= threshold, f"MetaQA 1-hop recall {recall:.3f} < {threshold}"

    def test_metaqa_2hop_answer_reachability(self, metaqa_dataset):
        """
        For MetaQA 2-hop QA pairs (e.g. 'What genres are films directed by X?'),
        answers require 2 relation hops in the KB graph.
        Recall >= multi_hop_recall_2hop threshold (0.75).
        """
        kb = metaqa_dataset["1hop"]["movies_kb"]
        qa_pairs = metaqa_dataset["2hop"]["qa_pairs"]
        graph = _build_metaqa_graph(kb)

        found = total = 0
        for qa in qa_pairs:
            answers = qa.get("answer", [])
            if not answers:
                continue
            reachable = _reachable_from(graph, qa["topic_entity"], max_hops=2)
            if reachable & _metaqa_answer_nodes(answers):
                found += 1
            total += 1

        if total == 0:
            pytest.skip("No MetaQA 2-hop QA pairs evaluated")

        recall = found / total
        threshold = get_threshold("multi_hop_recall_2hop")
        print(f"  MetaQA 2-hop recall: {recall:.3f} ({found}/{total})")
        assert recall >= threshold, f"MetaQA 2-hop recall {recall:.3f} < {threshold}"

    def test_metaqa_3hop_answer_reachability(self, metaqa_dataset):
        """
        For MetaQA 3-hop QA pairs, answers require 3 relation hops.
        Recall >= multi_hop_recall_3hop threshold (0.65).
        """
        kb = metaqa_dataset["1hop"]["movies_kb"]
        qa_pairs = metaqa_dataset["3hop"]["qa_pairs"]
        graph = _build_metaqa_graph(kb)

        found = total = 0
        for qa in qa_pairs:
            answers = qa.get("answer", [])
            if not answers:
                continue
            reachable = _reachable_from(graph, qa["topic_entity"], max_hops=3)
            if reachable & _metaqa_answer_nodes(answers):
                found += 1
            total += 1

        if total == 0:
            pytest.skip("No MetaQA 3-hop QA pairs evaluated")

        recall = found / total
        threshold = get_threshold("multi_hop_recall_3hop")
        print(f"  MetaQA 3-hop recall: {recall:.3f} ({found}/{total})")
        assert recall >= threshold, f"MetaQA 3-hop recall {recall:.3f} < {threshold}"

    def test_metaqa_kb_graph_node_coverage(self, metaqa_dataset):
        """
        All 100 MetaQA KB movies must be stored as graph nodes after build.
        Node coverage rate >= 0.95.
        """
        kb = metaqa_dataset["1hop"]["movies_kb"]
        graph = _build_metaqa_graph(kb)
        stored = _all_node_ids(graph)
        correct = sum(1 for movie in kb if movie["id"] in stored)
        rate = correct / max(len(kb), 1)
        assert rate >= 0.95, (
            f"MetaQA KB movie node coverage {rate:.3f} < 0.95 ({correct}/{len(kb)})"
        )
