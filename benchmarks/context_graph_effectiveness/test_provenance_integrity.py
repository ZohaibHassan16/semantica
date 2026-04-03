from __future__ import annotations

import os
import tempfile
import time

from semantica.provenance.integrity import compute_checksum, verify_checksum
from semantica.provenance.manager import ProvenanceManager
from semantica.provenance.schemas import ProvenanceEntry, SourceReference
from semantica.provenance.storage import SQLiteStorage


def test_lineage_completeness():
    manager = ProvenanceManager()
    root = manager.track_entity("doc1", source="doc1", metadata={"content": "Company A acquired B"})
    child = manager.track_entity("entity_a", source="doc1", parent_entity_id="doc1", metadata={"label": "ORG"})
    lineage = manager.get_lineage("entity_a")
    sources = set(lineage.get("source_documents", []))
    completeness = 1.0 if "doc1" in sources and lineage.get("entity_count", 0) >= 1 else 0.0
    assert completeness == 1.0


def test_source_citation_accuracy():
    manager = ProvenanceManager()
    source = SourceReference(document="doi:10.1000/182", metadata={"page": 5, "quote": "Findings"})
    manager.track_entity("citation_entity", source=source.document, metadata=source.metadata)
    record = manager.get_provenance("citation_entity")
    assert record is not None
    assert record["metadata"].get("page") == 5
    assert record["source_document"] == "doi:10.1000/182"


def test_checksum_integrity():
    entry = ProvenanceEntry(entity_id="1", entity_type="test", activity_id="test", source_document="test")
    checksum = compute_checksum(entry)
    assert verify_checksum(entry, checksum)
    entry.confidence += 1.0
    assert not verify_checksum(entry, checksum)


def test_sqlite_persistence_round_trip():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        storage = SQLiteStorage(path)
        entry = ProvenanceEntry(entity_id="test_id", entity_type="test", activity_id="test", source_document="test")
        storage.store(entry)
        data = SQLiteStorage(path).retrieve("test_id")
        assert data is not None
        assert data.entity_id == "test_id"
    finally:
        os.remove(path)


def test_provenance_overhead():
    manager = ProvenanceManager()
    start = time.perf_counter()
    for index in range(100):
        manager.track_entity(f"entity_{index}", source="doc1", metadata={"index": index})
    elapsed = time.perf_counter() - start
    average_ms = elapsed / 100 * 1000
    assert average_ms < 15
