import type { ApiEdge, ApiNode } from "./types";
import type { NodeAttributes } from "../../store/graphStore";
import { GRAPH_THEME, clamp, hashString } from "./graphConfig";

const SEMANTIC_COLOR_FIELDS = [
  "community",
  "cluster",
  "module",
  "group",
  "category",
  "domain",
  "layer",
  "source",
  "nodeType",
] as const;

type SemanticField = (typeof SEMANTIC_COLOR_FIELDS)[number];

function normalizedEntropy(counts: number[], total: number): number {
  if (counts.length <= 1 || total <= 0) {
    return 0;
  }

  let entropy = 0;
  for (const count of counts) {
    const probability = count / total;
    entropy -= probability * Math.log(probability);
  }

  return entropy / Math.log(counts.length);
}

function getSemanticFieldValue(attributes: Pick<NodeAttributes, "nodeType" | "properties">, field: SemanticField): string | null {
  if (field === "nodeType") {
    return typeof attributes.nodeType === "string" && attributes.nodeType.trim() ? attributes.nodeType : null;
  }

  const value = attributes.properties?.[field];
  return typeof value === "string" && value.trim() ? value : null;
}

function structuralColorKey(nodeId: string, attributes: Pick<NodeAttributes, "nodeType">): string {
  const shard = hashString(nodeId) % GRAPH_THEME.nodes.palette.length;
  return `${attributes.nodeType || "entity"}:${shard}`;
}

export function chooseColorAccessor(
  nodes: Array<{ id: string; attributes: Pick<NodeAttributes, "nodeType" | "properties"> }>,
): (nodeId: string, attributes: Pick<NodeAttributes, "nodeType" | "properties">) => string {
  let bestField: SemanticField | null = null;
  let bestScore = 0;

  for (const field of SEMANTIC_COLOR_FIELDS) {
    const counts = new Map<string, number>();
    let covered = 0;

    for (const node of nodes) {
      const value = getSemanticFieldValue(node.attributes, field);
      if (!value) {
        continue;
      }
      covered += 1;
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }

    const uniqueCount = counts.size;
    if (covered === 0 || uniqueCount <= 1) {
      continue;
    }

    const countValues = [...counts.values()];
    const coverage = covered / nodes.length;
    const dominantRatio = Math.max(...countValues) / covered;
    const entropy = normalizedEntropy(countValues, covered);
    const diversity = Math.min(uniqueCount, GRAPH_THEME.nodes.palette.length) / GRAPH_THEME.nodes.palette.length;
    const score = entropy * 0.6 + diversity * 0.25 + coverage * 0.15;
    const informativeEnough = coverage >= 0.4 && entropy >= 0.42 && dominantRatio <= 0.8;

    if (!informativeEnough) {
      continue;
    }

    if (score > bestScore) {
      bestField = field;
      bestScore = score;
    }
  }

  if (bestField) {
    return (nodeId, attributes) => getSemanticFieldValue(attributes, bestField) ?? structuralColorKey(nodeId, attributes);
  }

  return (nodeId, attributes) => structuralColorKey(nodeId, attributes);
}

export function computeDegreeMap(nodes: ApiNode[], edges: ApiEdge[]): Map<string, number> {
  const degreeByNode = new Map<string, number>();
  for (const node of nodes) {
    degreeByNode.set(node.id, 0);
  }

  for (const edge of edges) {
    degreeByNode.set(edge.source, (degreeByNode.get(edge.source) ?? 0) + 1);
    degreeByNode.set(edge.target, (degreeByNode.get(edge.target) ?? 0) + 1);
  }

  return degreeByNode;
}

export function computePageRank(nodes: ApiNode[], edges: ApiEdge[], iterations = 18, damping = 0.85): Map<string, number> {
  const nodeIds = nodes.map((node) => node.id);
  const nodeCount = nodeIds.length;
  const score = new Map<string, number>();
  const inbound = new Map<string, string[]>();
  const outbound = new Map<string, number>();

  for (const nodeId of nodeIds) {
    score.set(nodeId, 1 / Math.max(nodeCount, 1));
    inbound.set(nodeId, []);
    outbound.set(nodeId, 0);
  }

  for (const edge of edges) {
    inbound.get(edge.target)?.push(edge.source);
    outbound.set(edge.source, (outbound.get(edge.source) ?? 0) + 1);
  }

  for (let iteration = 0; iteration < iterations; iteration += 1) {
    const next = new Map<string, number>();
    let danglingMass = 0;

    for (const nodeId of nodeIds) {
      if ((outbound.get(nodeId) ?? 0) === 0) {
        danglingMass += score.get(nodeId) ?? 0;
      }
    }

    for (const nodeId of nodeIds) {
      let incoming = 0;
      for (const sourceId of inbound.get(nodeId) ?? []) {
        const outDegree = outbound.get(sourceId) ?? 1;
        incoming += (score.get(sourceId) ?? 0) / Math.max(outDegree, 1);
      }

      const distributedDangling = danglingMass / Math.max(nodeCount, 1);
      const nextScore = (1 - damping) / Math.max(nodeCount, 1) + damping * (incoming + distributedDangling);
      next.set(nodeId, nextScore);
    }

    next.forEach((value, key) => score.set(key, value));
  }

  const maxScore = Math.max(...score.values(), 1);
  score.forEach((value, key) => score.set(key, value / maxScore));
  return score;
}

export function computeNodeSize(nodeId: string, degreeByNode: Map<string, number>, pageRank: Map<string, number>): number {
  const degree = degreeByNode.get(nodeId) ?? 0;
  const maxDegree = Math.max(...degreeByNode.values(), 1);
  const normalizedLogDegree = Math.log(degree + 1) / Math.log(maxDegree + 1);
  const normalizedPageRank = pageRank.get(nodeId) ?? normalizedLogDegree;
  return clamp(2.5, 2.5 + 12 * normalizedLogDegree + 7 * normalizedPageRank, 22);
}

export function computeEdgeSize(weight: number | undefined): number {
  const safeWeight = Number.isFinite(weight) ? Math.max(Number(weight), 0) : 0;
  return clamp(0.5, 0.6 + Math.sqrt(safeWeight || 0.04), 2.4);
}

export function deterministicPosition(nodeId: string, index: number, total: number): { x: number; y: number } {
  const seed = hashString(`${nodeId}:${index}:${total}`) ^ 0x9e3779b9;
  let state = seed || 0x12345678;
  const next = () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };

  const angle = next() * Math.PI * 2;
  const radius = Math.sqrt(next()) * Math.min(90 + Math.sqrt(total) * 0.55, 170);
  const spread = 0.82 + Math.min(index / Math.max(total, 1), 0.18);
  return {
    x: Math.cos(angle) * radius * spread,
    y: Math.sin(angle) * radius * spread,
  };
}

export function colorForNodeKey(key: string): string {
  return GRAPH_THEME.nodes.palette[hashString(key) % GRAPH_THEME.nodes.palette.length];
}
