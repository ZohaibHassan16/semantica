import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ApiEdge, ApiNode, GraphDataSnapshot, GraphLoadProgress, GraphLayoutSource } from "./types";

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
      progress: total ? 0.45 + Math.min(collected.length / Math.max(total, 1), 1) * 0.33 : 0.68,
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

function hasUsableCoordinate(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

interface UseGraphDataOptions {
  enabled?: boolean;
  onProgress?: (progress: GraphLoadProgress) => void;
}

export function useGraphData(options: UseGraphDataOptions = {}) {
  const { enabled = true, onProgress } = options;

  return useQuery<GraphDataSnapshot>({
    queryKey: ["graph", "runtime-snapshot"],
    enabled,
    staleTime: Infinity,
    queryFn: async ({ signal }): Promise<GraphDataSnapshot> => {
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

      const nodes = await fetchAllNodes(signal, onProgress);
      const nodeIds = new Set(nodes.map((node) => node.id));
      const edges = await fetchAllEdges(
        signal,
        nodeIds,
        { loaded: nodes.length, total: nodes.length },
        onProgress,
      );

      onProgress?.({
        phase: "edges",
        nodesLoaded: nodes.length,
        nodesTotal: nodes.length,
        edgesLoaded: edges.length,
        edgesTotal: edges.length,
        message: "Preparing graph runtime",
        progress: 0.78,
      });

      return {
        nodes,
        edges,
        summary: {
          nodeCount: nodes.length,
          edgeCount: edges.length,
          loadTimeMs: Math.round(performance.now() - startedAt),
          hasCoordinates: nodes.some((node) => hasUsableCoordinate(node.x) && hasUsableCoordinate(node.y)),
          layoutSource: (nodes.some((node) => hasUsableCoordinate(node.x) && hasUsableCoordinate(node.y))
            ? "provided"
            : "runtime") as GraphLayoutSource,
          layoutReady: nodes.some((node) => hasUsableCoordinate(node.x) && hasUsableCoordinate(node.y)),
        },
        fetchedAt: Date.now(),
      };
    },
  });
}

export function useReloadGraphData() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["graph", "runtime-snapshot"] });
}
