import { useEffect, useMemo, useRef, useCallback, forwardRef, useImperativeHandle } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import { graph, type EdgeAttributes, type NodeAttributes } from "../../store/graphStore";

export interface GraphCanvasHandle {
  getSigma: () => Sigma | null;
  fitView: () => void;
  focusNode: (nodeId: string) => void;
}

export type GraphViewMode = "focused" | "full";

export interface GraphCanvasProps {
  onNodeClick: (nodeId: string) => void;
  selectedNodeId: string;
  isLayoutRunning: boolean;
  viewMode: GraphViewMode;
  className?: string;
}

const FA2_SETTINGS = {
  iterations: 50,
  settings: {
    barnesHutOptimize: true,
    barnesHutTheta: 0.5,
    adjustSizes: false,
    gravity: 1,
    slowDown: 10,
  },
};

const SIGMA_SETTINGS = {
  allowInvalidContainer: true,
  labelRenderedSizeThreshold: 6,
  defaultNodeType: "circle",
  defaultEdgeType: "arrow",
  hideEdgesOnMove: true,
  webGLTarget: "webgl2" as const,
};

const MAX_FOCUS_NEIGHBORS = 16;
const FOCUS_RING_CAPACITY = 6;
const FOCUS_RING_GAP = 260;
const FOCUS_PRIMARY_LABELS = 6;
const FULL_GRAPH_BACKGROUND_NODE_ALPHA = 0.035;
const FULL_GRAPH_BACKGROUND_NODE_SCALE = 0.09;
const FOCUS_SELECTED_COLOR = "#f2b66d";

function withAlpha(color: string | undefined, alpha: number): string {
  if (!color) {
    return `rgba(130, 145, 165, ${alpha})`;
  }

  if (color.startsWith("#")) {
    const hex = color.slice(1);
    const normalized = hex.length === 3
      ? hex.split("").map((char) => `${char}${char}`).join("")
      : hex;

    if (normalized.length === 6) {
      const red = Number.parseInt(normalized.slice(0, 2), 16);
      const green = Number.parseInt(normalized.slice(2, 4), 16);
      const blue = Number.parseInt(normalized.slice(4, 6), 16);
      return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
    }
  }

  if (color.startsWith("rgba(")) {
    return color.replace(/rgba\(([^)]+),\s*[\d.]+\)/, `rgba($1, ${alpha})`);
  }

  if (color.startsWith("rgb(")) {
    return color.replace("rgb(", "rgba(").replace(")", `, ${alpha})`);
  }

  return `rgba(130, 145, 165, ${alpha})`;
}

function getEdgeWeightBetween(source: string, target: string): number {
  let weight = 0;

  if (graph.hasDirectedEdge(source, target)) {
    const attrs = graph.getDirectedEdgeAttributes(source, target) as { weight?: number };
    weight = Math.max(weight, Number(attrs?.weight ?? 0));
  }

  if (graph.hasDirectedEdge(target, source)) {
    const attrs = graph.getDirectedEdgeAttributes(target, source) as { weight?: number };
    weight = Math.max(weight, Number(attrs?.weight ?? 0));
  }

  return weight;
}

function rankNeighbors(nodeId: string): string[] {
  return graph
    .neighbors(nodeId)
    .map((neighborId) => ({
      id: neighborId,
      weight: getEdgeWeightBetween(nodeId, neighborId),
      degree: graph.degree(neighborId),
    }))
    .sort((left, right) => {
      if (right.weight !== left.weight) {
        return right.weight - left.weight;
      }
      if (right.degree !== left.degree) {
        return right.degree - left.degree;
      }
      return left.id.localeCompare(right.id);
    })
    .map((item) => item.id);
}

function buildFocusSet(nodeId: string): Set<string> {
  const ranked = rankNeighbors(nodeId).slice(0, MAX_FOCUS_NEIGHBORS);
  return new Set<string>([nodeId, ...ranked]);
}

function createFocusedGraph(nodeId: string): Graph<NodeAttributes, EdgeAttributes> {
  const focused = new Graph<NodeAttributes, EdgeAttributes>({
    type: "directed",
    multi: false,
    allowSelfLoops: false,
  });

  const rankedNeighbors = rankNeighbors(nodeId).slice(0, MAX_FOCUS_NEIGHBORS);
  const focusIds = new Set<string>([nodeId, ...rankedNeighbors]);
  const labelledNeighborIds = new Set(rankedNeighbors.slice(0, FOCUS_PRIMARY_LABELS));

  const addNode = (id: string, attrs: NodeAttributes) => {
    if (!focused.hasNode(id)) {
      focused.addNode(id, attrs);
    }
  };

  const selectedAttrs = graph.getNodeAttributes(nodeId) as NodeAttributes;
  addNode(nodeId, {
    ...selectedAttrs,
    x: 0,
    y: 0,
    size: Math.max(Number(selectedAttrs.size || 6), 22),
    color: FOCUS_SELECTED_COLOR,
    label: selectedAttrs.label,
  });

  rankedNeighbors.forEach((neighborId, index) => {
    const baseAttrs = graph.getNodeAttributes(neighborId) as NodeAttributes;
    const ring = Math.floor(index / FOCUS_RING_CAPACITY);
    const ringIndex = index % FOCUS_RING_CAPACITY;
    const itemsInRing = Math.min(
      FOCUS_RING_CAPACITY,
      rankedNeighbors.length - ring * FOCUS_RING_CAPACITY,
    );
    const radius = FOCUS_RING_GAP * (ring + 1);
    const angle = (Math.PI * 2 * ringIndex) / itemsInRing - Math.PI / 2;

    addNode(neighborId, {
      ...baseAttrs,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      size: Math.max(Number(baseAttrs.size || 4), 10),
      color: String(baseAttrs.color || "#58a6ff"),
      label: labelledNeighborIds.has(neighborId) ? baseAttrs.label : "",
    });
  });

  for (const source of focusIds) {
    for (const target of focusIds) {
      if (source === target || !graph.hasDirectedEdge(source, target)) {
        continue;
      }
      const attrs = graph.getDirectedEdgeAttributes(source, target) as EdgeAttributes;
      const touchesSelected = source === nodeId || target === nodeId;
      focused.mergeDirectedEdge(source, target, {
        ...attrs,
        size: touchesSelected ? 2.4 : 1.2,
        color: touchesSelected ? "rgba(105, 190, 255, 0.95)" : "rgba(160, 174, 255, 0.28)",
      });
    }
  }

  return focused;
}

function applyFullGraphHighlight(sigma: Sigma, nodeId: string) {
  if (!graph.hasNode(nodeId)) {
    sigma.setSetting("nodeReducer", null);
    sigma.setSetting("edgeReducer", null);
    sigma.refresh();
    return;
  }

  const focusIds = buildFocusSet(nodeId);
  const rankedNeighbors = rankNeighbors(nodeId).slice(0, MAX_FOCUS_NEIGHBORS);
  const labelledIds = new Set(rankedNeighbors.slice(0, FOCUS_PRIMARY_LABELS));

  sigma.setSetting("nodeReducer", (node, data) => {
    if (node === nodeId) {
      return {
        ...data,
        color: FOCUS_SELECTED_COLOR,
        size: Math.max(Number(data.size || 5), 18),
        forceLabel: true,
        label: data.label,
        zIndex: 3,
      };
    }

    if (focusIds.has(node)) {
      return {
        ...data,
        color: String(data.color || "#58a6ff"),
        size: Math.max(Number(data.size || 4), 8.5),
        forceLabel: labelledIds.has(node),
        label: labelledIds.has(node) ? data.label : "",
        zIndex: 2,
      };
    }

    return {
      ...data,
      color: withAlpha(String(data.color || "#8291a5"), FULL_GRAPH_BACKGROUND_NODE_ALPHA),
      label: "",
      size: Math.max(Number(data.size || 2) * FULL_GRAPH_BACKGROUND_NODE_SCALE, 0.18),
      zIndex: 0,
    };
  });

  sigma.setSetting("edgeReducer", (edge, data) => {
    const [source, target] = graph.extremities(edge);
    const touchesSelected = source === nodeId || target === nodeId;
    const inFocus = focusIds.has(source) && focusIds.has(target);

    if (touchesSelected) {
      return {
        ...data,
        color: "rgba(105, 190, 255, 0.95)",
        size: Math.max(Number(data.size || 1), 2.2),
        zIndex: 2,
      };
    }

    if (inFocus) {
      return {
        ...data,
        color: "rgba(88, 166, 255, 0.16)",
        size: Math.max(Number(data.size || 1), 0.9),
        zIndex: 1,
      };
    }

    return {
      ...data,
      hidden: true,
      zIndex: 0,
    };
  });

  sigma.refresh();
}

function clearGraphHighlight(sigma: Sigma) {
  sigma.setSetting("nodeReducer", null);
  sigma.setSetting("edgeReducer", null);
  sigma.refresh();
}

export const GraphCanvas = forwardRef<GraphCanvasHandle, GraphCanvasProps>(
  function GraphCanvas({ onNodeClick, selectedNodeId, isLayoutRunning, viewMode, className }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const sigmaRef = useRef<Sigma | null>(null);
    const fa2Ref = useRef<FA2Layout | null>(null);

    const isFocusedView = viewMode === "focused" && Boolean(selectedNodeId) && graph.hasNode(selectedNodeId);
    const displayGraph = useMemo(() => {
      if (isFocusedView && selectedNodeId) {
        return createFocusedGraph(selectedNodeId);
      }
      return graph;
    }, [isFocusedView, selectedNodeId]);

    const fitCurrentView = useCallback(() => {
      const sigma = sigmaRef.current;
      if (!sigma) {
        return;
      }

      if (isFocusedView) {
        sigma.getCamera().animatedReset({ duration: 350 });
        sigma.refresh();
        return;
      }

      if (selectedNodeId) {
        applyFullGraphHighlight(sigma, selectedNodeId);
      }

      sigma.getCamera().animatedReset({ duration: 350 });
    }, [isFocusedView, selectedNodeId]);

    useImperativeHandle(ref, () => ({
      getSigma: () => sigmaRef.current,
      fitView: () => fitCurrentView(),
      focusNode: () => fitCurrentView(),
    }), [fitCurrentView]);

    useEffect(() => {
      if (!containerRef.current) return;

      const sigma = new Sigma(displayGraph, containerRef.current, SIGMA_SETTINGS);
      sigmaRef.current = sigma;

      const resizeObserver = new ResizeObserver(() => {
        if (containerRef.current && containerRef.current.offsetWidth > 0) {
          sigma.refresh();
        }
      });
      resizeObserver.observe(containerRef.current);

      sigma.on("clickNode", ({ node }) => onNodeClick(node));
      sigma.on("clickStage", () => onNodeClick(""));

      requestAnimationFrame(() => {
        fitCurrentView();
      });

      return () => {
        resizeObserver.disconnect();
        sigma.kill();
        sigmaRef.current = null;
      };
    }, [displayGraph, fitCurrentView, onNodeClick]);

    useEffect(() => {
      const sigma = sigmaRef.current;
      if (!sigma || displayGraph !== graph) {
        return;
      }

      if (selectedNodeId) {
        applyFullGraphHighlight(sigma, selectedNodeId);
        return;
      }

      clearGraphHighlight(sigma);
    }, [displayGraph, selectedNodeId]);

    useEffect(() => {
      if (selectedNodeId || isFocusedView) {
        fa2Ref.current?.stop();
        return;
      }

      if (isLayoutRunning) {
        if (!fa2Ref.current) {
          fa2Ref.current = new FA2Layout(graph, FA2_SETTINGS);
        }
        fa2Ref.current.start();
      } else {
        fa2Ref.current?.stop();
      }

      return () => {
        fa2Ref.current?.stop();
      };
    }, [isFocusedView, isLayoutRunning, selectedNodeId]);

    useEffect(() => {
      return () => {
        fa2Ref.current?.kill();
        fa2Ref.current = null;
      };
    }, []);

    const handleFitView = useCallback(() => {
      fitCurrentView();
    }, [fitCurrentView]);

    return (
      <div style={{ position: "relative", width: "100%", height: "100%" }}>
        <div
          ref={containerRef}
          className={className}
          style={{ width: "100%", height: "100%", background: "transparent" }}
        />
        <button
          id="graph-fit-view-btn"
          onClick={handleFitView}
          style={{
            position: "absolute",
            bottom: 24,
            left: 24,
            padding: "8px 16px",
            background: "rgba(31, 111, 235, 0.85)",
            color: "#fff",
            border: "1px solid rgba(88,166,255,0.3)",
            borderRadius: 6,
            cursor: "pointer",
            fontWeight: 600,
            zIndex: 10,
            backdropFilter: "blur(8px)",
            fontSize: 13,
          }}
        >
          Fit View
        </button>
      </div>
    );
  }
);
