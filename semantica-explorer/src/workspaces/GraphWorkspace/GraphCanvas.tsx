import { useEffect, useMemo, useRef, useCallback, forwardRef, useImperativeHandle, useState, type ReactNode } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import { graph, type EdgeAttributes, type NodeAttributes } from "../../store/graphStore";
import type { GraphBehavior, GraphBehaviorContext, GraphBehaviorActionRequest } from "./behaviors/types";
import { hoverActivationBehavior } from "./behaviors/hoverActivationBehavior";
import { clickSelectionBehavior } from "./behaviors/clickSelectionBehavior";
import { focusCameraBehavior } from "./behaviors/focusCameraBehavior";
import { createSearchFocusBehavior } from "./behaviors/searchFocusBehavior";
import { createPathHighlightBehavior } from "./behaviors/pathHighlightBehavior";
import { fitViewBehavior } from "./behaviors/fitViewBehavior";
import { createViewModeSwitchBehavior } from "./behaviors/viewModeSwitchBehavior";
import {
  GRAPH_THEME,
  getZoomTier,
  type GraphEdgeVisualState,
  type GraphNodeVisualState,
  type GraphTheme,
  type GraphZoomTier,
  withAlpha,
} from "./graphTheme";
import type { GraphCameraState, GraphInteractionState, GraphLayoutStatus, GraphViewMode } from "./types";
import type { GraphPluginRuntime } from "./plugins";

export type { GraphViewMode } from "./types";

export interface GraphCanvasHandle {
  getSigma: () => Sigma | null;
  fitView: () => void;
  focusNode: (nodeId: string) => void;
}

export interface GraphCanvasProps {
  onNodeClick: (nodeId: string) => void;
  selectedNodeId: string;
  activePath?: string[];
  isLayoutRunning: boolean;
  onLayoutRunningChange?: (running: boolean) => void;
  layoutSource?: string;
  onLayoutStatusChange?: (status: GraphLayoutStatus) => void;
  viewMode: GraphViewMode;
  className?: string;
  pluginOverlays?: ReactNode[];
  onPluginRuntimeChange?: (runtime: GraphPluginRuntime | null) => void;
  onInteractionStateChange?: (interactionState: GraphInteractionState) => void;
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
  labelRenderedSizeThreshold: 3,
  defaultNodeType: "circle",
  defaultEdgeType: "line",
  hideEdgesOnMove: true,
  webGLTarget: "webgl2" as const,
};

const MAX_FOCUS_NEIGHBORS = GRAPH_THEME.focus.maxNeighbors;
const FOCUS_RING_CAPACITY = GRAPH_THEME.focus.ringCapacity;
const FOCUS_RING_GAP = GRAPH_THEME.focus.ringGap;
const FOCUS_PRIMARY_LABELS = GRAPH_THEME.focus.primaryLabels;

function buildPathEdgeSet(path: string[]): Set<string> {
  const edgeIds = new Set<string>();
  for (let index = 0; index < path.length - 1; index += 1) {
    edgeIds.add(`${path[index]}::${path[index + 1]}`);
    edgeIds.add(`${path[index + 1]}::${path[index]}`);
  }
  return edgeIds;
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

function resolveNodeColor(theme: GraphTheme, state: GraphNodeVisualState, attrs: NodeAttributes, fallbackColor?: string) {
  const baseColor = String(attrs.baseColor || fallbackColor || theme.palette.semantic[0]);

  switch (theme.nodes.states[state].color) {
    case "selected":
      return theme.palette.accent.selected;
    case "hovered":
      return theme.palette.accent.hovered;
    case "path":
      return theme.palette.accent.path;
    case "muted":
      return String(attrs.mutedColor || withAlpha(baseColor, theme.nodes.mutedAlpha));
    case "base":
    default:
      return baseColor;
  }
}

function resolveEdgeColor(theme: GraphTheme, state: GraphEdgeVisualState, attrs: EdgeAttributes, fallbackColor?: string) {
  const baseColor = String(attrs.baseColor || fallbackColor || theme.palette.muted.edgeInspection);

  switch (theme.edges.states[state].color) {
    case "hover":
      return theme.palette.accent.hovered;
    case "path":
      return theme.palette.accent.path;
    case "focus":
      return theme.palette.muted.edgeFocus;
    case "overview":
      return theme.palette.muted.edgeOverview;
    case "structure":
      return theme.palette.muted.edgeStructure;
    case "inspection":
      return theme.palette.muted.edgeInspection;
    case "muted":
      return String(attrs.mutedColor || theme.palette.muted.edgeOverview);
    default:
      return baseColor;
  }
}

function resolveNodeVisualState(
  nodeId: string,
  hoveredNodeId: string | null,
  selectedNodeId: string,
  focusIds: Set<string>,
  pathNodeIds: Set<string>,
): GraphNodeVisualState {
  if (hoveredNodeId && nodeId === hoveredNodeId) {
    return "hovered";
  }
  if (selectedNodeId && nodeId === selectedNodeId) {
    return "selected";
  }
  if (pathNodeIds.has(nodeId)) {
    return "path";
  }
  if (focusIds.has(nodeId)) {
    return "neighbor";
  }
  if (hoveredNodeId || selectedNodeId || pathNodeIds.size > 0) {
    return "muted";
  }
  return "default";
}

function resolveEdgeVisualState(
  source: string,
  target: string,
  hoveredNodeId: string | null,
  selectedNodeId: string,
  focusIds: Set<string>,
  pathEdgeIds: Set<string>,
): GraphEdgeVisualState {
  const edgeKey = `${source}::${target}`;
  const primaryNodeId = hoveredNodeId || selectedNodeId;

  if (pathEdgeIds.has(edgeKey)) {
    return "path";
  }

  if (primaryNodeId && (source === primaryNodeId || target === primaryNodeId)) {
    return hoveredNodeId ? "hovered" : "selected";
  }

  if (focusIds.has(source) && focusIds.has(target)) {
    return "neighbor";
  }

  if (hoveredNodeId || selectedNodeId || pathEdgeIds.size > 0) {
    return "muted";
  }

  return "default";
}

function resolveNodeStyle(
  theme: GraphTheme,
  zoomTier: GraphZoomTier,
  state: GraphNodeVisualState,
  attrs: NodeAttributes,
  label: string,
) {
  const tierConfig = theme.zoomTiers[zoomTier];
  const stateConfig = theme.nodes.states[state];
  const baseSize = Number(attrs.baseSize || attrs.size || 4);
  const labelPriority = Number(attrs.labelPriority ?? 0);
  const forceVisibleState = theme.labels.forceVisibleStates.includes(state);
  const color = resolveNodeColor(theme, state, attrs, attrs.color);
  const sizeMultiplier = state === "default" ? tierConfig.nodeScale : stateConfig.sizeMultiplier;
  const forceLabel = forceVisibleState || stateConfig.forceLabel || labelPriority >= tierConfig.labelThreshold;

  return {
    color,
    size: Math.max(baseSize * sizeMultiplier, stateConfig.minSize),
    forceLabel,
    label: forceLabel ? label : "",
    zIndex: forceLabel && stateConfig.zIndex === 0 ? 1 : stateConfig.zIndex,
    hidden: false,
    borderColor: attrs.strokeColor || attrs.borderColor || theme.palette.background.nodeBorder,
    borderSize: attrs.borderSize,
  };
}

function resolveEdgeType(
  theme: GraphTheme,
  zoomTier: GraphZoomTier,
  state: GraphEdgeVisualState,
  attrs: EdgeAttributes,
) {
  if (theme.edges.states[state].forceArrow) {
    return "arrow";
  }

  if (state === "neighbor") {
    return zoomTier === "inspection" || Boolean(attrs.isBidirectional) ? "arrow" : "line";
  }

  if (state !== "default") {
    return attrs.type || "line";
  }

  return Number(attrs.visualPriority ?? 0) >= theme.zoomTiers[zoomTier].arrowPriorityThreshold || Boolean(attrs.isBidirectional)
    ? "arrow"
    : "line";
}

function resolveEdgeStyle(
  theme: GraphTheme,
  zoomTier: GraphZoomTier,
  state: GraphEdgeVisualState,
  attrs: EdgeAttributes,
) {
  const tierConfig = theme.zoomTiers[zoomTier];
  const stateConfig = theme.edges.states[state];
  const baseSize = Number(attrs.baseSize || attrs.size || 0.9);
  const visualPriority = Number(attrs.visualPriority ?? 0);
  const belowPriorityThreshold = state === "default"
    && visualPriority < tierConfig.edgePriorityThreshold
    && !attrs.isBidirectional;

  if (stateConfig.hide || belowPriorityThreshold) {
    return {
      hidden: true,
      zIndex: 0,
    };
  }

  const sizeMultiplier = state === "default" ? tierConfig.edgeSizeScale : stateConfig.sizeMultiplier;

  return {
    hidden: false,
    type: resolveEdgeType(theme, zoomTier, state, attrs),
    color: resolveEdgeColor(theme, state, attrs, attrs.color),
    size: Math.max(baseSize * sizeMultiplier, stateConfig.minSize),
    zIndex: stateConfig.zIndex,
  };
}

function createFocusedGraph(nodeId: string, activePath: string[]): Graph<NodeAttributes, EdgeAttributes> {
  const focused = new Graph<NodeAttributes, EdgeAttributes>({
    type: "directed",
    multi: false,
    allowSelfLoops: false,
  });

  const rankedNeighbors = rankNeighbors(nodeId).slice(0, MAX_FOCUS_NEIGHBORS);
  const focusIds = new Set<string>([nodeId, ...rankedNeighbors]);
  const labelledNeighborIds = new Set(rankedNeighbors.slice(0, FOCUS_PRIMARY_LABELS));
  const pathNodeIds = new Set(activePath);
  const pathEdgeIds = buildPathEdgeSet(activePath);

  const addNode = (id: string, attrs: NodeAttributes) => {
    if (!focused.hasNode(id)) {
      focused.addNode(id, attrs);
    }
  };

  const selectedAttrs = graph.getNodeAttributes(nodeId) as NodeAttributes;
  const selectedState = resolveNodeStyle(GRAPH_THEME, "inspection", "selected", selectedAttrs, selectedAttrs.label);
  addNode(nodeId, {
    ...selectedAttrs,
    x: 0,
    y: 0,
    color: selectedState.color,
    size: Math.max(selectedState.size, 22),
    label: selectedState.label,
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
    const visualState: GraphNodeVisualState = pathNodeIds.has(neighborId)
      ? "path"
      : labelledNeighborIds.has(neighborId)
        ? "neighbor"
        : "default";
    const style = resolveNodeStyle(
      GRAPH_THEME,
      "inspection",
      visualState,
      {
        ...baseAttrs,
        labelPriority: labelledNeighborIds.has(neighborId) || pathNodeIds.has(neighborId)
          ? Math.max(Number(baseAttrs.labelPriority ?? 0), 1)
          : 0,
      },
      baseAttrs.label,
    );

    addNode(neighborId, {
      ...baseAttrs,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      color: style.color,
      size: Math.max(style.size, 8.5),
      label: style.label,
    });
  });

  for (const source of focusIds) {
    for (const target of focusIds) {
      if (source === target || !graph.hasDirectedEdge(source, target)) {
        continue;
      }
      const attrs = graph.getDirectedEdgeAttributes(source, target) as EdgeAttributes;
      const state: GraphEdgeVisualState = pathEdgeIds.has(`${source}::${target}`)
        ? "path"
        : source === nodeId || target === nodeId
          ? "selected"
          : "neighbor";
      const style = resolveEdgeStyle(GRAPH_THEME, "inspection", state, attrs);
      focused.mergeDirectedEdge(source, target, {
        ...attrs,
        type: style.type,
        size: style.size,
        color: style.color,
      });
    }
  }

  return focused;
}

function applySceneState(
  sigma: Sigma,
  interactionState: GraphInteractionState,
) {
  const { zoomTier, hoveredNodeId, selectedNodeId, activePath } = interactionState;
  const primaryNodeId = hoveredNodeId || selectedNodeId;
  const focusIds = primaryNodeId && graph.hasNode(primaryNodeId) ? buildFocusSet(primaryNodeId) : new Set<string>();
  const pathNodeIds = new Set(activePath);
  const pathEdgeIds = buildPathEdgeSet(activePath);

  sigma.setSetting("nodeReducer", (node, data) => {
    const attrs = data as NodeAttributes;
    const state = resolveNodeVisualState(node, hoveredNodeId, selectedNodeId, focusIds, pathNodeIds);
    const style = resolveNodeStyle(GRAPH_THEME, zoomTier, state, attrs, data.label);

    return {
      ...data,
      color: style.color,
      size: style.size,
      forceLabel: style.forceLabel,
      label: style.label,
      zIndex: style.zIndex,
      hidden: style.hidden,
      borderColor: style.borderColor,
      borderSize: style.borderSize,
    };
  });

  sigma.setSetting("edgeReducer", (edge, data) => {
    const attrs = data as EdgeAttributes;
    const [source, target] = graph.extremities(edge);
    const state = resolveEdgeVisualState(source, target, hoveredNodeId, selectedNodeId, focusIds, pathEdgeIds);
    const style = resolveEdgeStyle(GRAPH_THEME, zoomTier, state, attrs);

    return {
      ...data,
      hidden: style.hidden,
      type: style.type,
      color: style.color,
      size: style.size,
      zIndex: style.zIndex,
    };
  });

  sigma.refresh();
}

function createInteractionState(
  hoveredNodeId: string | null,
  selectedNodeId: string,
  activePath: string[],
  viewMode: GraphViewMode,
  zoomTier: GraphZoomTier,
  isLayoutRunning: boolean,
): GraphInteractionState {
  return {
    hoveredNodeId,
    selectedNodeId,
    focusedNodeId: selectedNodeId,
    activePath,
    viewMode,
    zoomTier,
    isLayoutRunning,
  };
}

function dispatchBehaviorAction(
  behaviors: GraphBehavior[],
  context: GraphBehaviorContext,
  action: GraphBehaviorActionRequest,
) {
  for (const behavior of behaviors) {
    if (behavior.performAction?.(context, action)) {
      return;
    }
  }
}

export const GraphCanvas = forwardRef<GraphCanvasHandle, GraphCanvasProps>(
  function GraphCanvas(
    {
      onNodeClick,
      selectedNodeId,
      activePath = [],
      isLayoutRunning,
      viewMode,
      className,
      pluginOverlays = [],
      onPluginRuntimeChange,
      onInteractionStateChange,
    },
    ref,
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const overlayRef = useRef<HTMLCanvasElement>(null);
    const sigmaRef = useRef<Sigma | null>(null);
    const fa2Ref = useRef<FA2Layout | null>(null);
    const behaviorContextRef = useRef<GraphBehaviorContext | null>(null);
    const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
    const [zoomTier, setZoomTier] = useState<GraphZoomTier>("overview");

    const behaviors = useMemo<GraphBehavior[]>(
      () => [
        hoverActivationBehavior,
        clickSelectionBehavior,
        focusCameraBehavior,
        createSearchFocusBehavior(),
        createPathHighlightBehavior(),
        fitViewBehavior,
        createViewModeSwitchBehavior(),
      ],
      [],
    );

    const isFocusedView = viewMode === "focused" && Boolean(selectedNodeId) && graph.hasNode(selectedNodeId);
    const displayGraph = useMemo(() => {
      if (isFocusedView && selectedNodeId) {
        return createFocusedGraph(selectedNodeId, activePath);
      }
      return graph;
    }, [activePath, isFocusedView, selectedNodeId]);

    const interactionState = useMemo(
      () => createInteractionState(hoveredNodeId, selectedNodeId, activePath, viewMode, zoomTier, isLayoutRunning),
      [activePath, hoveredNodeId, isLayoutRunning, selectedNodeId, viewMode, zoomTier],
    );
    const interactionStateRef = useRef<GraphInteractionState>(interactionState);
    interactionStateRef.current = interactionState;

    const focusNodeInView = useCallback((nodeId: string) => {
      const sigma = sigmaRef.current;
      if (!sigma) {
        return;
      }

      if (isFocusedView) {
        sigma.getCamera().animatedReset({ duration: GRAPH_THEME.motion.cameraMs });
        sigma.refresh();
        return;
      }

      const data = sigma.getNodeDisplayData(nodeId);
      if (!data) {
        sigma.getCamera().animatedReset({ duration: GRAPH_THEME.motion.cameraMs });
        return;
      }

      void sigma.getCamera().animate(
        { x: data.x, y: data.y, ratio: 0.3 },
        { duration: GRAPH_THEME.motion.cameraMs, easing: "quadraticOut" },
      );
    }, [isFocusedView]);

    const fitCurrentView = useCallback(() => {
      const sigma = sigmaRef.current;
      if (!sigma) {
        return;
      }

      if (selectedNodeId) {
        focusNodeInView(selectedNodeId);
        return;
      }

      sigma.getCamera().animatedReset({ duration: GRAPH_THEME.motion.cameraMs });
    }, [focusNodeInView, selectedNodeId]);

    const dispatchAction = useCallback((action: GraphBehaviorActionRequest) => {
      const context = behaviorContextRef.current;
      if (!context) {
        return;
      }

      dispatchBehaviorAction(behaviors, context, action);
    }, [behaviors]);

    const getBehaviorContext = useCallback((sigma?: Sigma | null): GraphBehaviorContext | null => {
      const runtimeSigma = sigma ?? sigmaRef.current;
      if (!runtimeSigma) {
        return null;
      }

      const context: GraphBehaviorContext = {
        sigma: runtimeSigma,
        graph,
        displayGraph,
        getInteractionState: () => interactionStateRef.current,
        setHoveredNodeId,
        onNodeSelectionChange: onNodeClick,
        focusNodeInView,
        fitCurrentView,
        dispatchAction,
      };
      behaviorContextRef.current = context;
      return context;
    }, [displayGraph, dispatchAction, fitCurrentView, focusNodeInView, onNodeClick]);

    const dispatchToBehaviors = useCallback((
      hook: "onNodeEnter" | "onNodeLeave" | "onNodeClick" | "onStageClick" | "onCameraChange",
      ...args: unknown[]
    ) => {
      const context = getBehaviorContext();
      if (!context) {
        return;
      }

      for (const behavior of behaviors) {
        const handler = behavior[hook];
        if (typeof handler === "function") {
          (handler as (...handlerArgs: unknown[]) => void)(context, ...args);
        }
      }
    }, [behaviors, getBehaviorContext]);

    useImperativeHandle(ref, () => ({
      getSigma: () => sigmaRef.current,
      fitView: () => dispatchAction({ type: "fitView" }),
      focusNode: (nodeId: string) => dispatchAction({ type: "focusNode", nodeId }),
    }), [dispatchAction]);

    useEffect(() => {
      if (!containerRef.current) return;

      const sigma = new Sigma(displayGraph, containerRef.current, SIGMA_SETTINGS);
      sigmaRef.current = sigma;
      onPluginRuntimeChange?.({
        sigma,
        graph,
        displayGraph,
      });
      const camera = sigma.getCamera();
      const context = getBehaviorContext(sigma);

      if (context) {
        for (const behavior of behaviors) {
          behavior.attach(context);
        }
      }

      const syncTier = () => {
        const cameraState: GraphCameraState = {
          x: camera.getState().x,
          y: camera.getState().y,
          ratio: camera.getState().ratio,
        };
        const nextTier = getZoomTier(cameraState.ratio);
        setZoomTier((current) => (current === nextTier ? current : nextTier));
        dispatchToBehaviors("onCameraChange", cameraState);
      };

      const resizeObserver = new ResizeObserver(() => {
        if (containerRef.current && containerRef.current.offsetWidth > 0) {
          sigma.refresh();
        }
      });
      resizeObserver.observe(containerRef.current);

      camera.on("updated", syncTier);
      sigma.on("clickNode", ({ node }) => dispatchToBehaviors("onNodeClick", node));
      sigma.on("clickStage", () => dispatchToBehaviors("onStageClick"));
      sigma.on("enterNode", ({ node }) => dispatchToBehaviors("onNodeEnter", node));
      sigma.on("leaveNode", ({ node }) => dispatchToBehaviors("onNodeLeave", node));

      requestAnimationFrame(() => {
        syncTier();
        dispatchAction({ type: "fitView" });
      });

      return () => {
        if (context) {
          for (const behavior of behaviors) {
            behavior.detach(context);
          }
        }
        camera.off("updated", syncTier);
        resizeObserver.disconnect();
        sigma.kill();
        behaviorContextRef.current = null;
        sigmaRef.current = null;
        onPluginRuntimeChange?.(null);
      };
    }, [behaviors, dispatchAction, dispatchToBehaviors, displayGraph, getBehaviorContext, onPluginRuntimeChange]);

    useEffect(() => {
      const context = getBehaviorContext();
      if (!context) {
        return;
      }

      for (const behavior of behaviors) {
        behavior.onStateChange?.(context, interactionState);
      }

      for (const behavior of behaviors) {
        behavior.apply?.(context, interactionState);
      }
      onInteractionStateChange?.(interactionState);
    }, [behaviors, getBehaviorContext, interactionState, onInteractionStateChange]);

    useEffect(() => {
      const sigma = sigmaRef.current;
      if (!sigma || displayGraph !== graph) {
        return;
      }
      applySceneState(sigma, interactionState);
    }, [displayGraph, interactionState]);

    useEffect(() => {
      const sigma = sigmaRef.current;
      const overlay = overlayRef.current;
      const container = containerRef.current;
      if (!sigma || !overlay || !container) {
        return;
      }

      let frame = 0;

      const draw = () => {
        const rect = container.getBoundingClientRect();
        const pixelRatio = window.devicePixelRatio || 1;
        if (overlay.width !== Math.floor(rect.width * pixelRatio) || overlay.height !== Math.floor(rect.height * pixelRatio)) {
          overlay.width = Math.floor(rect.width * pixelRatio);
          overlay.height = Math.floor(rect.height * pixelRatio);
          overlay.style.width = `${rect.width}px`;
          overlay.style.height = `${rect.height}px`;
        }

        const context = overlay.getContext("2d");
        if (!context) {
          frame = window.requestAnimationFrame(draw);
          return;
        }

        context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
        context.clearRect(0, 0, rect.width, rect.height);

        const primaryNodeId = interactionState.hoveredNodeId || interactionState.selectedNodeId;
        const nodesToGlow = new Set<string>([
          ...interactionState.activePath,
          ...(primaryNodeId ? [primaryNodeId] : []),
        ]);
        const edgePairs = buildPathEdgeSet(interactionState.activePath);
        const now = performance.now() / 1000;

        nodesToGlow.forEach((nodeId) => {
          const displayData = sigma.getNodeDisplayData(nodeId);
          if (!displayData) return;
          const point = sigma.graphToViewport({ x: displayData.x, y: displayData.y });
          const glowColor = nodeId === primaryNodeId
            ? withAlpha(GRAPH_THEME.palette.accent.hovered, GRAPH_THEME.overlays.hoverGlowAlpha)
            : withAlpha(GRAPH_THEME.palette.accent.path, GRAPH_THEME.overlays.pathGlowAlpha);
          const radius = Math.max(
            displayData.size * GRAPH_THEME.overlays.glowRadiusMultiplier,
            GRAPH_THEME.overlays.minGlowRadius,
          );
          const gradient = context.createRadialGradient(point.x, point.y, 0, point.x, point.y, radius);
          gradient.addColorStop(0, glowColor);
          gradient.addColorStop(1, "rgba(0,0,0,0)");
          context.fillStyle = gradient;
          context.beginPath();
          context.arc(point.x, point.y, radius, 0, Math.PI * 2);
          context.fill();
        });

        if (interactionState.activePath.length > 1) {
          for (let index = 0; index < interactionState.activePath.length - 1; index += 1) {
            const sourceId = interactionState.activePath[index];
            const targetId = interactionState.activePath[index + 1];
            if (!edgePairs.has(`${sourceId}::${targetId}`)) continue;
            const sourceData = sigma.getNodeDisplayData(sourceId);
            const targetData = sigma.getNodeDisplayData(targetId);
            if (!sourceData || !targetData) continue;
            const source = sigma.graphToViewport({ x: sourceData.x, y: sourceData.y });
            const target = sigma.graphToViewport({ x: targetData.x, y: targetData.y });
            const t = ((now * 0.22) + index * 0.17) % 1;
            const x = source.x + (target.x - source.x) * t;
            const y = source.y + (target.y - source.y) * t;
            const glow = context.createRadialGradient(x, y, 0, x, y, GRAPH_THEME.overlays.pulseRadius);
            glow.addColorStop(0, GRAPH_THEME.palette.accent.path);
            glow.addColorStop(1, "rgba(0,0,0,0)");
            context.fillStyle = glow;
            context.beginPath();
            context.arc(x, y, GRAPH_THEME.overlays.pulseRadius, 0, Math.PI * 2);
            context.fill();
          }
        }

        frame = window.requestAnimationFrame(draw);
      };

      draw();
      return () => {
        window.cancelAnimationFrame(frame);
      };
    }, [interactionState]);

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
        <canvas
          ref={overlayRef}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
            zIndex: 4,
          }}
        />
        {pluginOverlays.length ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              pointerEvents: "none",
              zIndex: 6,
            }}
          >
            {pluginOverlays.map((overlay, index) => (
              <div key={`graph-plugin-overlay-${index}`} style={{ position: "absolute", inset: 0 }}>
                {overlay}
              </div>
            ))}
          </div>
        ) : null}
        <button
          id="graph-fit-view-btn"
          onClick={handleFitView}
          style={{
            position: "absolute",
            bottom: 24,
            left: 24,
            padding: "8px 16px",
            background: "linear-gradient(135deg, rgba(27, 79, 170, 0.9), rgba(53, 123, 255, 0.84))",
            color: "#fff",
            border: `1px solid ${GRAPH_THEME.palette.background.shellBorder}`,
            borderRadius: 10,
            cursor: "pointer",
            fontWeight: 700,
            zIndex: 10,
            backdropFilter: "blur(10px)",
            boxShadow: `0 10px 28px ${GRAPH_THEME.palette.background.shellGlow}`,
            fontSize: 12,
            letterSpacing: "0.01em",
          }}
        >
          Fit View
        </button>
      </div>
    );
  }
);
