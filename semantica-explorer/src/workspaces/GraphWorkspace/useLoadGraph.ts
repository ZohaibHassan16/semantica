import { useQuery, useQueryClient } from "@tanstack/react-query";
import { batchMergeEdges, batchMergeNodes, clearGraph } from "../../store/graphStore";
import type { EdgeAttributes, NodeAttributes } from "../../store/graphStore";

const GRAPH_PALETTE = [
  "#61afef",
  "#56b6c2",
  "#98c379",
  "#e5c07b",
  "#d19a66",
  "#e06c75",
  "#c678dd",
  "#7aa2f7",
  "#4fd1c5",
  "#f59e0b",
  "#fb7185",
  "#a3e635",
];

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

const hashCategory = (value: string): number => {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(index);
    hash |= 0;
  }
  return Math.abs(hash);
};

function getSemanticFieldValue(attributes: NodeAttributes, field: (typeof SEMANTIC_COLOR_FIELDS)[number]): string | null {
  if (field === "nodeType") {
    const value = attributes.nodeType;
    return typeof value === "string" && value.trim() ? value : null;
  }

  const value = attributes.properties?.[field];
  return typeof value === "string" && value.trim() ? value : null;
}

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

function chooseColorAccessor(
  nodes: Array<{ id: string; attributes: NodeAttributes }>,
): (nodeId: string, attributes: NodeAttributes) => string {
  let bestField: (typeof SEMANTIC_COLOR_FIELDS)[number] | null = null;
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
    const diversity = Math.min(uniqueCount, GRAPH_PALETTE.length) / GRAPH_PALETTE.length;
    const score = entropy * 0.65 + diversity * 0.2 + coverage * 0.15;

    const isInformative =
      coverage >= 0.45 &&
      entropy >= 0.45 &&
      dominantRatio <= 0.88;

    if (!isInformative) {
      continue;
    }

    if (score > bestScore) {
      bestField = field;
      bestScore = score;
    }
  }

  if (bestField) {
    return (_nodeId: string, attributes: NodeAttributes) =>
      getSemanticFieldValue(attributes, bestField) ?? structuralColorKey(_nodeId, attributes);
  }

  return (nodeId: string, attributes: NodeAttributes) => structuralColorKey(nodeId, attributes);
}

function structuralColorKey(nodeId: string, attributes: NodeAttributes): string {
  const shard = hashCategory(nodeId) % GRAPH_PALETTE.length;
  return `${attributes.nodeType || "entity"}:${shard}`;
}

interface ApiNode {
  id: string;
  type: string;
  content: string;
  properties: Record<string, unknown>;
  valid_from?: string | null;
  valid_until?: string | null;
}

interface ApiEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
  properties: Record<string, unknown>;
}

interface NodeListResponse {
  nodes: ApiNode[];
  total: number;
  skip: number;
  limit: number;
  next_cursor?: string | null;
}

interface EdgeListResponse {
  edges: ApiEdge[];
  total: number;
  skip: number;
  limit: number;
  next_cursor?: string | null;
}

export interface GraphLoadSummary {
  nodeCount: number;
  edgeCount: number;
  loadTimeMs: number;
}

export interface GraphLoadProgress {
  phase: "nodes" | "edges" | "styling" | "rendering";
  nodesLoaded: number;
  nodesTotal: number | null;
  edgesLoaded: number;
  edgesTotal: number | null;
  message: string;
  progress: number;
}

const PAGE_LIMIT = 1000;

async function fetchAllNodes(
  signal: AbortSignal,
  onProgress?: (progress: GraphLoadProgress) => void,
): Promise<ApiNode[]> {
  let cursor: string | null = null;
  const collected: ApiNode[] = [];
  let total: number | null = null;

  while (true) {
    const url = new URL("/api/graph/nodes", window.location.origin);
    url.searchParams.set("limit", String(PAGE_LIMIT));
    if (cursor) {
      url.searchParams.set("cursor", cursor);
    }

    const response = await fetch(url.toString(), { signal });
    if (!response.ok) {
      throw new Error(`Fetch failed: ${response.status}`);
    }

    const data: NodeListResponse = await response.json();
    if (!data.nodes?.length) {
      break;
    }

    total = data.total ?? total;
    collected.push(...data.nodes);
    onProgress?.({
      phase: "nodes",
      nodesLoaded: collected.length,
      nodesTotal: total,
      edgesLoaded: 0,
      edgesTotal: null,
      message: total
        ? `Loading nodes ${collected.length.toLocaleString()} of ${total.toLocaleString()}`
        : `Loading nodes ${collected.length.toLocaleString()}`,
      progress: total ? Math.min(collected.length / Math.max(total, 1), 0.45) : 0.18,
    });

    if (!data.next_cursor) {
      break;
    }
    cursor = data.next_cursor;
    await yieldToMain();
  }

  return collected;
}

async function fetchAllEdges(
  signal: AbortSignal,
  nodeIds: Set<string>,
  nodeProgress: { loaded: number; total: number | null },
  onProgress?: (progress: GraphLoadProgress) => void,
): Promise<ApiEdge[]> {
  let cursor: string | null = null;
  const collected: ApiEdge[] = [];
  let total: number | null = null;

  while (true) {
    const url = new URL("/api/graph/edges", window.location.origin);
    url.searchParams.set("limit", String(PAGE_LIMIT));
    if (cursor) {
      url.searchParams.set("cursor", cursor);
    }

    const response = await fetch(url.toString(), { signal });
    if (!response.ok) {
      throw new Error(`Fetch failed: ${response.status}`);
    }

    const data: EdgeListResponse = await response.json();
    if (!data.edges?.length) {
      break;
    }

    total = data.total ?? total;
    const validEdges = data.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
    collected.push(...validEdges);
    onProgress?.({
      phase: "edges",
      nodesLoaded: nodeProgress.loaded,
      nodesTotal: nodeProgress.total,
      edgesLoaded: collected.length,
      edgesTotal: total,
      message: total
        ? `Loading edges ${collected.length.toLocaleString()} of ${total.toLocaleString()}`
        : `Loading edges ${collected.length.toLocaleString()}`,
      progress: total ? 0.45 + Math.min(collected.length / Math.max(total, 1), 1) * 0.35 : 0.62,
    });

    if (!data.next_cursor) {
      break;
    }
    cursor = data.next_cursor;
    await yieldToMain();
  }

  return collected;
}

function yieldToMain(): Promise<void> {
  if ("scheduler" in window && typeof (window as Window & { scheduler?: { yield?: () => Promise<void> } }).scheduler?.yield === "function") {
    return (window as Window & { scheduler: { yield: () => Promise<void> } }).scheduler.yield();
  }
  return new Promise((resolve) => setTimeout(resolve, 0));
}

interface UseLoadGraphOptions {
  enabled?: boolean;
  onGraphReady?: (summary: GraphLoadSummary) => void;
  onProgress?: (progress: GraphLoadProgress) => void;
}

export function useLoadGraph(options: UseLoadGraphOptions = {}) {
  const { enabled = true, onGraphReady, onProgress } = options;

  return useQuery<GraphLoadSummary>({
    queryKey: ["graph", "full-load"],
    enabled,
    staleTime: Infinity,
    queryFn: async ({ signal }): Promise<GraphLoadSummary> => {
      const startedAt = performance.now();
      onProgress?.({
        phase: "nodes",
        nodesLoaded: 0,
        nodesTotal: null,
        edgesLoaded: 0,
        edgesTotal: null,
        message: "Preparing graph load",
        progress: 0.06,
      });

      const fetchedNodes = await fetchAllNodes(signal, onProgress);
      const nodeIds = new Set(fetchedNodes.map((node) => node.id));
      const fetchedEdges = await fetchAllEdges(
        signal,
        nodeIds,
        { loaded: fetchedNodes.length, total: fetchedNodes.length },
        onProgress,
      );

      const degreeByNode = new Map<string, number>();
      for (const nodeId of nodeIds) {
        degreeByNode.set(nodeId, 0);
      }
      for (const edge of fetchedEdges) {
        degreeByNode.set(edge.source, (degreeByNode.get(edge.source) ?? 0) + 1);
        degreeByNode.set(edge.target, (degreeByNode.get(edge.target) ?? 0) + 1);
      }

      const maxDegree = Math.max(...degreeByNode.values(), 1);
      const draftAttributes = fetchedNodes.map((node) => {
        const x = Number((node.properties as Record<string, unknown>)?.x ?? Math.random() * 1000 - 500);
        const y = Number((node.properties as Record<string, unknown>)?.y ?? Math.random() * 1000 - 500);
        return {
          id: node.id,
          attributes: {
            label: node.content || node.id,
            x,
            y,
            nodeType: node.type,
            content: node.content,
            valid_from: node.valid_from,
            valid_until: node.valid_until,
            properties: node.properties,
          } as NodeAttributes,
        };
      });

      onProgress?.({
        phase: "styling",
        nodesLoaded: fetchedNodes.length,
        nodesTotal: fetchedNodes.length,
        edgesLoaded: fetchedEdges.length,
        edgesTotal: fetchedEdges.length,
        message: "Computing graph styling",
        progress: 0.86,
      });

      const colorAccessor = chooseColorAccessor(draftAttributes);

      const nodesToMerge = draftAttributes.map(({ id, attributes }) => {
        const colorKey = colorAccessor(id, attributes);
        const colorIndex = hashCategory(colorKey) % GRAPH_PALETTE.length;
        const degree = degreeByNode.get(id) ?? 0;
        const minSize = 2;
        const maxSize = 25;
        const sizeRatio = Math.log(degree + 1) / Math.log(maxDegree + 1);
        const dynamicSize = minSize + (maxSize - minSize) * sizeRatio;
        return {
          id,
          attributes: {
            ...attributes,
            color: GRAPH_PALETTE[colorIndex],
            size: dynamicSize,
            borderColor: "#0d1117",
            borderSize: 0.5,
          } as NodeAttributes,
        };
      });

      const edgesToMerge = fetchedEdges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        attributes: {
          weight: edge.weight,
          edgeType: edge.type,
          properties: edge.properties,
          size: Number((edge.properties as Record<string, unknown>)?.size ?? 1),
          color: String((edge.properties as Record<string, unknown>)?.color ?? "#444C56"),
        } as EdgeAttributes,
      }));

      onProgress?.({
        phase: "rendering",
        nodesLoaded: nodesToMerge.length,
        nodesTotal: nodesToMerge.length,
        edgesLoaded: edgesToMerge.length,
        edgesTotal: edgesToMerge.length,
        message: "Rendering graph",
        progress: 0.96,
      });

      clearGraph();
      batchMergeNodes(nodesToMerge);
      batchMergeEdges(edgesToMerge);

      const summary = {
        nodeCount: nodesToMerge.length,
        edgeCount: edgesToMerge.length,
        loadTimeMs: Math.round(performance.now() - startedAt),
      } satisfies GraphLoadSummary;

      onProgress?.({
        phase: "rendering",
        nodesLoaded: summary.nodeCount,
        nodesTotal: summary.nodeCount,
        edgesLoaded: summary.edgeCount,
        edgesTotal: summary.edgeCount,
        message: "Graph ready",
        progress: 1,
      });

      onGraphReady?.(summary);
      return summary;
    },
  });
}

export function useReloadGraph() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["graph", "full-load"] });
}
