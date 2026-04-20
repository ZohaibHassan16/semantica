import test from "node:test";
import assert from "node:assert/strict";

import {
  batchMergeEdges,
  batchMergeNodes,
  clearGraph,
} from "../src/store/graphStore.ts";
import { resolveDisplayGraph } from "../src/workspaces/GraphWorkspace/graphSceneState.ts";

function addNode(id: string, semanticGroup = "entity") {
  batchMergeNodes([
    {
      id,
      attributes: {
        label: id,
        content: id,
        x: 0,
        y: 0,
        size: 8,
        color: "#63E6FF",
        baseColor: "#63E6FF",
        nodeType: semanticGroup,
        semanticGroup,
        properties: {},
      },
    },
  ]);
}

function addEdge(id: string, source: string, target: string, weight = 1) {
  batchMergeEdges([
    {
      id,
      source,
      target,
      attributes: {
        edgeType: "related_to",
        weight,
        properties: {},
      },
    },
  ]);
}

test.beforeEach(() => {
  clearGraph();
});

test.after(() => {
  clearGraph();
});

test("resolveDisplayGraph bundles parallel edges in full view", () => {
  addNode("a");
  addNode("b");
  addEdge("e1", "a", "b", 1);
  addEdge("e2", "a", "b", 2);

  const { graph } = resolveDisplayGraph("", [], [], "full", { aggregationEnabled: true });
  assert.equal(graph.size, 1);

  const edgeId = graph.edges()[0];
  const attrs = graph.getEdgeAttributes(edgeId) as {
    isAggregated?: boolean;
    aggregateCount?: number;
    rawEdgeIds?: string[];
    bundleKind?: string;
  };

  assert.equal(attrs.isAggregated, true);
  assert.equal(attrs.aggregateCount, 2);
  assert.deepEqual(new Set(attrs.rawEdgeIds ?? []), new Set(["e1", "e2"]));
  assert.equal(attrs.bundleKind, "parallel");
});

test("resolveDisplayGraph collapse keeps path neighbor visible", () => {
  addNode("center");
  for (let index = 0; index < 10; index += 1) {
    const neighbor = `n${index}`;
    addNode(neighbor);
    addEdge(`edge-${index}`, "center", neighbor, 1);
  }

  const { state } = resolveDisplayGraph("center", ["center", "n9"], [], "full", {
    aggregationEnabled: false,
    collapsedNeighborhoodNodeIds: ["center"],
  });

  assert.equal(state.selectedRootNodeId, "center");
  assert.equal(state.selectedVisibleNeighborIds.includes("n9"), true);
  assert.equal(state.selectedVisibleNeighborIds.length, 9);
  assert.equal(state.selectedCollapsedNeighborIds.length, 1);
});

test("resolveDisplayGraph grouped view emits community nodes and edges", () => {
  const left = ["a1", "a2", "a3", "a4"];
  const right = ["b1", "b2", "b3", "b4"];

  [...left, ...right].forEach((nodeId, index) => {
    addNode(nodeId, index < left.length ? "left" : "right");
  });

  let edgeIndex = 0;
  for (let i = 0; i < left.length; i += 1) {
    for (let j = 0; j < left.length; j += 1) {
      if (i !== j) {
        addEdge(`l-${edgeIndex++}`, left[i], left[j], 3);
      }
    }
  }

  for (let i = 0; i < right.length; i += 1) {
    for (let j = 0; j < right.length; j += 1) {
      if (i !== j) {
        addEdge(`r-${edgeIndex++}`, right[i], right[j], 3);
      }
    }
  }

  addEdge("bridge-1", "a1", "b1", 0.1);
  addEdge("bridge-2", "a2", "b2", 0.1);

  const { graph, state } = resolveDisplayGraph("", [], [], "grouped", { aggregationEnabled: true });

  assert.equal(state.groupedViewAvailable, true);

  const communityNodes = graph.nodes().filter((nodeId) => nodeId.startsWith("__community__"));
  assert.ok(communityNodes.length >= 2);

  const hasCommunityEdge = graph
    .edges()
    .map((edgeId) => graph.getEdgeAttributes(edgeId) as { bundleKind?: string; isAggregated?: boolean; aggregateCount?: number })
    .some((attrs) => attrs.bundleKind === "community" && attrs.isAggregated === true && Number(attrs.aggregateCount ?? 0) > 0);

  assert.equal(hasCommunityEdge, true);
});
