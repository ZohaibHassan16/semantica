from __future__ import annotations

import os
import tempfile
import time

from semantica.change_management.managers import TemporalVersionManager
from semantica.change_management.version_storage import SQLiteVersionStorage, compute_checksum


def _graph_v1() -> dict:
    return {
        "nodes": [
            {"id": "A", "type": "Entity", "properties": {"name": "Alice"}},
            {"id": "B", "type": "Entity", "properties": {"name": "Bob"}},
        ],
        "edges": [{"source_id": "A", "target_id": "B", "type": "KNOWS", "properties": {}}],
    }


def _graph_v2() -> dict:
    graph = _graph_v1()
    graph["nodes"].append({"id": "C", "type": "Entity", "properties": {"name": "Carol"}})
    graph["edges"].append({"source_id": "B", "target_id": "C", "type": "KNOWS", "properties": {}})
    return graph


def test_snapshot_fidelity():
    manager = TemporalVersionManager()
    graph = _graph_v1()
    snapshot = manager.create_snapshot(graph, "v1", "bench@example.com", "baseline")
    restored = manager.get_version("v1")
    assert restored is not None
    assert restored["nodes"] == snapshot["nodes"]
    assert restored["edges"] == snapshot["edges"]


def test_version_diff_correctness():
    manager = TemporalVersionManager()
    manager.create_snapshot(_graph_v1(), "v1", "bench@example.com", "baseline")
    manager.create_snapshot(_graph_v2(), "v2", "bench@example.com", "updated")
    diff = manager.compare_versions("v1", "v2")
    assert diff["summary"]["nodes_added"] == 1
    assert diff["summary"]["edges_added"] >= 0


def test_checksum_change_detection():
    graph = _graph_v1()
    checksum_v1 = compute_checksum(graph)
    mutated = _graph_v2()
    checksum_v2 = compute_checksum(mutated)
    assert checksum_v1 != checksum_v2


def test_sqlite_persistence():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        storage = SQLiteVersionStorage(path)
        snapshot = {
            "label": "v1",
            "timestamp": "2026-01-01T00:00:00",
            "author": "bench@example.com",
            "description": "baseline",
            "nodes": _graph_v1()["nodes"],
            "edges": _graph_v1()["edges"],
            "checksum": compute_checksum(_graph_v1()),
        }
        storage.save(snapshot)
        reloaded = SQLiteVersionStorage(path).get("v1")
        assert reloaded is not None
        assert reloaded["label"] == "v1"
        assert reloaded["nodes"] == snapshot["nodes"]
    finally:
        os.remove(path)


def test_version_manager_overhead():
    manager = TemporalVersionManager()
    graph = _graph_v1()
    start = time.perf_counter()
    for index in range(50):
        manager.create_snapshot(graph, f"v{index}", "bench@example.com", "perf")
    elapsed = time.perf_counter() - start
    average_seconds = elapsed / 50
    assert average_seconds < 0.10
