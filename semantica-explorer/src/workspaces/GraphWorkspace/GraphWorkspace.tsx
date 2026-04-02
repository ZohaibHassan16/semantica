/**
 * src/workspaces/GraphWorkspace/GraphWorkspace.tsx
 */
import { useState, useCallback } from "react";
import { GraphCanvas } from "./GraphCanvas";
import { useLoadGraph, useReloadGraph } from "./useLoadGraph";
import { graph } from "../../store/graphStore";

const HUD_CSS = `
  .palantir-bg {
    background: radial-gradient(ellipse at center, #0d1117 0%, #010409 100%);
  }
  .palantir-grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(88, 166, 255, 0.05) 1px, transparent 1px),
      linear-gradient(90deg, rgba(88, 166, 255, 0.05) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 1;
  }
  .palantir-vignette {
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at center, transparent 30%, rgba(1, 4, 9, 0.85) 100%);
    pointer-events: none;
    z-index: 2;
  }
  .glass-header {
    background: linear-gradient(180deg, rgba(13,17,23,0.85) 0%, rgba(13,17,23,0) 100%);
    border-bottom: 1px solid rgba(88,166,255,0.1);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
  }
  .glass-hud {
    background: linear-gradient(135deg, rgba(13,17,23,0.75), rgba(22,27,34,0.6));
    backdrop-filter: blur(16px) saturate(1.2);
    -webkit-backdrop-filter: blur(16px) saturate(1.2);
    border-left: 1px solid rgba(88,166,255,0.2);
    box-shadow: -8px 0 32px rgba(0,0,0,0.5), inset 1px 0 0 rgba(255,255,255,0.05);
  }
  .hud-scrollbar::-webkit-scrollbar { width: 4px; }
  .hud-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .hud-scrollbar::-webkit-scrollbar-thumb { background: rgba(88, 166, 255, 0.3); border-radius: 4px; }
`;

function NodePanel({ nodeId }: { nodeId: string }) {
  if (!nodeId) {
    return (
      <div style={{ padding: "32px 24px", textAlign: "center" }}>
        <p style={{ color: "#8b949e", fontSize: 14, margin: 0 }}>
          Select a node to view details
        </p>
      </div>
    );
  }

  const attrs = graph.getNodeAttributes(nodeId);

  return (
    <aside style={{ padding: 24 }}>
      <div style={{ borderBottom: "1px solid rgba(88, 166, 255, 0.2)", paddingBottom: 16, marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <span style={{ 
            background: attrs?.color || "#6c8ebf", 
            boxShadow: `0 0 10px ${attrs?.color || "#6c8ebf"}`,
            width: 8, height: 8, borderRadius: "50%", display: "inline-block" 
          }} />
          <span style={{ color: attrs?.color || "#6c8ebf", fontSize: 12, fontWeight: 600 }}>
            {attrs?.nodeType || "Entity"}
          </span>
        </div>
        <h3 style={{ margin: 0, color: "#ffffff", fontSize: 20, fontWeight: 600 }}>
          {String(attrs?.label ?? nodeId)}
        </h3>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {Object.entries(attrs?.properties || {}).map(([k, v]) => (
          <div key={k} style={{ background: "rgba(0,0,0,0.2)", padding: "10px 14px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.05)" }}>
            <div style={{ color: "rgba(88, 166, 255, 0.7)", fontSize: 11, marginBottom: 4 }}>
              {k}
            </div>
            <div style={{ color: "#e6edf3", fontSize: 13, fontFamily: "monospace", wordBreak: "break-word" }}>
              {typeof v === "object" ? JSON.stringify(v) : String(v)}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

export function GraphWorkspace() {
  const [selectedNodeId, setSelectedNodeId] = useState<string>("");
  const [isLayoutRunning, setIsLayoutRunning] = useState(false);
  const reload = useReloadGraph();

  const handleNodeClick = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId);
  }, []);

  const { data: summary, isLoading, isError, error } = useLoadGraph({
    enabled: true,
    onGraphReady: () => {
      setIsLayoutRunning(true);
    },
  });

  return (

    <div className="palantir-bg" style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden" }}>
      <style>{HUD_CSS}</style>

      <div className="palantir-grid" />
      <div className="palantir-vignette" />

      <div style={{ position: "absolute", inset: 0, zIndex: 3 }}>
        <GraphCanvas
          onNodeClick={handleNodeClick}
          selectedNodeId={selectedNodeId}
          isLayoutRunning={isLayoutRunning}
        />
      </div>

      <div style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 10 }}>
        
        <header className="glass-header" style={{ pointerEvents: "auto", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 24px" }}>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <h2 style={{ margin: 0, fontSize: 18, color: "#ffffff", fontWeight: 600 }}>Graph Explorer</h2>
            
            {isLoading && <span style={{ color: "rgba(88,166,255,0.8)", fontSize: 13 }}>Loading data...</span>}
            {summary && (
              <span style={{ background: "rgba(88,166,255,0.1)", color: "#58a6ff", padding: "4px 10px", borderRadius: 4, fontSize: 12, border: "1px solid rgba(88,166,255,0.2)" }}>
                {summary.nodeCount.toLocaleString()} nodes · {summary.edgeCount.toLocaleString()} edges
              </span>
            )}
            {isError && (
              <span style={{ color: "#ff7b72", fontSize: 13 }}>Error: {(error as Error).message}</span>
            )}
          </div>

          <div style={{ display: "flex", gap: 12 }}>
            <button
              onClick={() => setIsLayoutRunning((v) => !v)}
              style={btnStyle(isLayoutRunning ? "rgba(56, 139, 253, 0.15)" : "rgba(255,255,255,0.05)", isLayoutRunning ? "#58a6ff" : "#e6edf3")}
              disabled={isLoading}
            >
              <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: isLayoutRunning ? "#58a6ff" : "#8b949e", marginRight: 8 }} />
              {isLayoutRunning ? "Pause Layout" : "Run Layout"}
            </button>
            <button onClick={reload} style={btnStyle("rgba(255,255,255,0.05)", "#e6edf3")} disabled={isLoading}>
              ↺ Reload
            </button>
          </div>
        </header>

        <div 
          className="glass-hud hud-scrollbar" 
          style={{ 
            pointerEvents: "auto", 
            position: "absolute", 
            right: 0, 
            top: 60, 
            bottom: 0, 
            width: 360, 
            overflowY: "auto",
            transition: "transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
            transform: selectedNodeId ? "translateX(0)" : "translateX(100%)"
          }}
        >
          <NodePanel nodeId={selectedNodeId} />
        </div>
        
      </div>
    </div>
  );
}

const btnStyle = (bg: string, color: string): React.CSSProperties => ({ 
  background: bg, 
  color, 
  border: "1px solid rgba(255,255,255,0.1)", 
  borderRadius: 4, 
  padding: "8px 16px", 
  cursor: "pointer", 
  fontSize: 13, 
  fontWeight: 500,
  transition: "all 0.2s",
  backdropFilter: "blur(4px)"
});