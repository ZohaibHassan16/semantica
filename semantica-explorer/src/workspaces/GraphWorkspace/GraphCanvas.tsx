/**
 * src/workspaces/GraphWorkspace/GraphCanvas.tsx
 */
import { useEffect, useRef, useState, useCallback } from "react";
import Sigma from "sigma";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import { graph } from "../../store/graphStore";

export interface GraphCanvasProps {
  onNodeClick: (nodeId: string) => void;
  selectedNodeId: string; 
  targetCameraNodeId?: string;
  isolatedClusterId?: string | null;
  isLayoutRunning: boolean;
  className?: string;
}

function extractClusterId(properties: Record<string, unknown> | null | undefined): string | null {
  if (!properties || typeof properties !== "object") return null;

  const raw =
    properties.clusterId ??
    properties.cluster_id ??
    properties.cluster ??
    properties.community ??
    properties.community_id ??
    properties.group;

  if (raw == null) return null;
  const text = String(raw).trim();
  return text ? text : null;
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

export function GraphCanvas({ onNodeClick, selectedNodeId, targetCameraNodeId, isolatedClusterId, isLayoutRunning, className }: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const fa2Ref = useRef<FA2Layout | null>(null);
  const isolatedNodeSetRef = useRef<Set<string> | null>(null);


  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  useEffect(() => {
    if (!isolatedClusterId) {
      isolatedNodeSetRef.current = null;
      return;
    }

    const nodeSet = new Set<string>();
    graph.forEachNode((nodeId) => {
      const attrs = graph.getNodeAttributes(nodeId) as { properties?: Record<string, unknown> };
      const clusterId = extractClusterId(attrs?.properties);
      if (clusterId === isolatedClusterId) {
        nodeSet.add(nodeId);
      }
    });

    isolatedNodeSetRef.current = nodeSet;
  }, [isolatedClusterId]);

  useEffect(() => {
    if (!containerRef.current || sigmaRef.current) return;

    const sigma = new Sigma(graph, containerRef.current, SIGMA_SETTINGS);
    sigmaRef.current = sigma;

    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.current && containerRef.current.offsetWidth > 0) {
        sigma.refresh();
      }
    });
    resizeObserver.observe(containerRef.current);

    // Click Events
    sigma.on("clickNode", ({ node }) => {
      onNodeClick(node);
    });

    sigma.on("clickStage", () => {
      onNodeClick("");
    });

    // Hover Events
    sigma.on("enterNode", ({ node }) => setHoveredNode(node));
    sigma.on("leaveNode", () => setHoveredNode(null));

    return () => {
      resizeObserver.disconnect();
      sigma.kill();
      sigmaRef.current = null;
    };
  }, [onNodeClick]);



  useEffect(() => {
    const sigma = sigmaRef.current;
    if (!sigma) return;

  
    const activeNode = hoveredNode || selectedNodeId;
    const isClusterFilterActive = !!isolatedClusterId;
    const isolatedNodeSet = isolatedNodeSetRef.current;

    const isNodeAllowedByCluster = (nodeId: string): boolean => {
      if (!isClusterFilterActive) return true;
      return isolatedNodeSet?.has(nodeId) ?? false;
    };
    

    const isValidActiveNode = activeNode && graph.hasNode(activeNode);
    
   
    const activeNeighbors = isValidActiveNode && isNodeAllowedByCluster(activeNode) ? new Set(graph.neighbors(activeNode)) : new Set();

    if (!isValidActiveNode && !isClusterFilterActive) {
     
      sigma.setSetting("nodeReducer", null);
      
      sigma.setSetting("edgeReducer", (_edge, data) => ({
        ...data,
        color: "#161b22",
        size: Math.max(0.5, (data.size || 1) * 0.5),
        zIndex: 0,
      }));
    } else {
      sigma.setSetting("nodeReducer", (node, data) => {
        if (!isNodeAllowedByCluster(node)) {
          return {
            ...data,
            color: "#10151b",
            borderColor: "#0d1117",
            label: "",
            zIndex: 0,
          };
        }

        const isFocused = node === activeNode;
        const isNeighbor = activeNeighbors.has(node);

        if (isFocused || isNeighbor) {
          return {
            ...data,
            zIndex: isFocused ? 2 : 1,
            borderColor: isFocused ? "#ffffff" : data.borderColor,
            borderSize: isFocused ? 2 : data.borderSize,
          };
        }

        // Mute all other nodes into the background
        return {
          ...data,
          color: "#1c2128", 
          borderColor: "#0d1117",
          label: "",
          zIndex: 0,
        };
      });

      sigma.setSetting("edgeReducer", (edge, data) => {
        if (isClusterFilterActive) {
          const source = graph.source(edge);
          const target = graph.target(edge);
          if (!isNodeAllowedByCluster(source) || !isNodeAllowedByCluster(target)) {
            return { ...data, hidden: true };
          }
        }

        if (isValidActiveNode && graph.hasExtremity(edge, activeNode)) {
          return {
            ...data,
            color: "#58a6ff",
            size: (data.size || 1) * 2, 
            zIndex: 1,
          };
        }

        if (isClusterFilterActive && !isValidActiveNode) {
          return {
            ...data,
            color: data.color || "#444C56",
            size: data.size || 1,
            hidden: false,
          };
        }
      
        return { ...data, hidden: true };
      });
    }

    sigma.refresh();
  }, [hoveredNode, selectedNodeId, isolatedClusterId]); 


  useEffect(() => {
    const sigma = sigmaRef.current;
    if (!sigma || !targetCameraNodeId) return;
    if (!graph.hasNode(targetCameraNodeId)) return;

    const attrs = graph.getNodeAttributes(targetCameraNodeId);
    const x = attrs?.x;
    const y = attrs?.y;

    if (typeof x !== "number" || typeof y !== "number") return;

    sigma.getCamera().animate(
      { x, y, ratio: 0.25 },
      { duration: 500 }
    );
  }, [targetCameraNodeId]);



  useEffect(() => {
    if (isLayoutRunning) {
      if (!fa2Ref.current) {
        fa2Ref.current = new FA2Layout(graph, FA2_SETTINGS);
      }
      fa2Ref.current.start();
    } else {
      fa2Ref.current?.stop();
    }

    return () => {
      fa2Ref.current?.kill();
      fa2Ref.current = null;
    };
  }, [isLayoutRunning]);


  const handleFitView = useCallback(() => {
    sigmaRef.current?.getCamera().animatedReset({ duration: 500 });
  }, []);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div ref={containerRef} className={className} style={{ width: "100%", height: "100%", background: "transparent" }} />
      <button
        onClick={handleFitView}
        style={{
          position: "absolute", bottom: 24, left: 24, padding: "8px 16px", 
          background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6,
          cursor: "pointer", fontWeight: 600, zIndex: 10,
        }}
      >
        Fit View
      </button>
    </div>
  );
}