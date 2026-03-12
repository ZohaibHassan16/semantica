"""
Provenance Tracker for Knowledge Graph entities.

Tracks the sources and lineage of entities and relationships.
"""

from typing import Any, Dict, List, Optional


class ProvenanceTracker:
    """
    Tracks provenance (source lineage) for knowledge graph entities.

    Usage:
        tracker = ProvenanceTracker()
        tracker.track_entity("E1", "doc1.txt", metadata={"type": "file"})
        sources = tracker.get_all_sources("E1")
    """

    def __init__(self):
        self._records: Dict[str, List[Dict[str, Any]]] = {}

    def track_entity(
        self,
        entity_id: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record that entity_id was derived from source."""
        if entity_id not in self._records:
            self._records[entity_id] = []
        entry: Dict[str, Any] = {"source": source}
        if metadata:
            entry.update(metadata)
        self._records[entity_id].append(entry)

    def get_all_sources(self, entity_id: str) -> List[Dict[str, Any]]:
        """Return all provenance records for entity_id."""
        return self._records.get(entity_id, [])

    def clear(self, entity_id: Optional[str] = None) -> None:
        """Clear provenance records."""
        if entity_id:
            self._records.pop(entity_id, None)
        else:
            self._records.clear()
