import { useCallback, useMemo, useState } from "react";
import { graph } from "../../../store/graphStore";

interface AnalyticsDashboardProps {
  onSelectNode: (nodeId: string) => void;
  onIsolateCluster: (clusterId: string | null) => void;
  isolatedClusterId: string | null;
  refreshKey?: number;
}

interface RankedNode {
  id: string;
  label: string;
  type: string;
  degree: number;
  importance: number;
}

interface ClusterSummary {
  id: string;
  size: number;
  sampleNodeId: string;
}

const MAX_TOP_NODES = 20;
const MAX_CLUSTERS = 20;

type RankingMode = "degree" | "importance";

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

function extractImportance(properties: Record<string, unknown> | null | undefined, fallbackDegree: number): number {
  if (!properties || typeof properties !== "object") return fallbackDegree;

  const raw =
    properties.importance ??
    properties.centrality ??
    properties.pagerank ??
    properties.score;

  const value = Number(raw);
  return Number.isFinite(value) ? value : fallbackDegree;
}

function insertTopBy<T>(
  list: T[],
  item: T,
  limit: number,
  scoreFn: (value: T) => number
): void {
  if (list.length === 0) {
    list.push(item);
    return;
  }

  const itemScore = scoreFn(item);
  if (list.length >= limit && itemScore <= scoreFn(list[list.length - 1])) {
    return;
  }

  let insertAt = list.length;
  for (let i = 0; i < list.length; i++) {
    if (itemScore > scoreFn(list[i])) {
      insertAt = i;
      break;
    }
  }

  list.splice(insertAt, 0, item);
  if (list.length > limit) {
    list.length = limit;
  }
}

export function AnalyticsDashboard({
  onSelectNode,
  onIsolateCluster,
  isolatedClusterId,
  refreshKey,
}: AnalyticsDashboardProps) {
  const [rankingMode, setRankingMode] = useState<RankingMode>("degree");
  const [isCentralityOpen, setCentralityOpen] = useState(true);
  const [isClustersOpen, setClustersOpen] = useState(true);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoveredClusterId, setHoveredClusterId] = useState<string | null>(null);

  const model = useMemo(() => {
    const topByDegree: RankedNode[] = [];
    const topByImportance: RankedNode[] = [];

    const clusterCounts = new Map<string, number>();
    const clusterSampleNode = new Map<string, string>();

    graph.forEachNode((nodeId) => {
      const attrs = graph.getNodeAttributes(nodeId) as Record<string, unknown>;
      const properties = (attrs?.properties ?? {}) as Record<string, unknown>;

      const degree = graph.degree(nodeId);
      const importance = extractImportance(properties, degree);

      const rankedNode: RankedNode = {
        id: nodeId,
        label: String(attrs?.label ?? attrs?.content ?? nodeId),
        type: String(attrs?.nodeType ?? "entity"),
        degree,
        importance,
      };

      insertTopBy(topByDegree, rankedNode, MAX_TOP_NODES, (item) => item.degree);
      insertTopBy(topByImportance, rankedNode, MAX_TOP_NODES, (item) => item.importance);

      const clusterId = extractClusterId(properties);
      if (!clusterId) return;

      clusterCounts.set(clusterId, (clusterCounts.get(clusterId) ?? 0) + 1);
      if (!clusterSampleNode.has(clusterId)) {
        clusterSampleNode.set(clusterId, nodeId);
      }
    });

    const topClusters: ClusterSummary[] = [];
    clusterCounts.forEach((size, id) => {
      const sampleNodeId = clusterSampleNode.get(id);
      if (!sampleNodeId) return;
      insertTopBy(topClusters, { id, size, sampleNodeId }, MAX_CLUSTERS, (item) => item.size);
    });

    return {
      nodesByDegree: topByDegree,
      nodesByImportance: topByImportance,
      clusters: topClusters,
      totalClusters: clusterCounts.size,
    };
  }, [graph.order, graph.size, refreshKey]);

  const rankedNodes = rankingMode === "degree" ? model.nodesByDegree : model.nodesByImportance;

  const memoizedRowButtonStyle = useCallback(
    (hovered: boolean): React.CSSProperties => ({
      width: "100%",
      borderRadius: 8,
      border: "1px solid rgba(255,255,255,0.1)",
      background: hovered ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.03)",
      marginBottom: 6,
      padding: "8px 10px",
      cursor: "pointer",
      transition: "background 160ms ease, border-color 160ms ease, transform 160ms ease",
      transform: hovered ? "translateX(2px)" : "translateX(0)",
    }),
    []
  );

  const memoizedPillStyle = useCallback(
    (active: boolean): React.CSSProperties => ({
      border: `1px solid ${active ? "rgba(116,176,255,0.52)" : "rgba(255,255,255,0.14)"}`,
      borderRadius: 999,
      padding: "4px 11px",
      fontSize: 11,
      cursor: "pointer",
      background: active
        ? "linear-gradient(135deg, rgba(53,121,221,0.32), rgba(24,74,143,0.2))"
        : "rgba(255,255,255,0.05)",
      color: active ? "#9fc7ff" : "#e6edf3",
      transition: "background 160ms ease, border-color 160ms ease, color 160ms ease",
    }),
    []
  );

  return (
    <section
      style={{
        padding: "14px 16px 12px 16px",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        background: "linear-gradient(165deg, rgba(13,17,23,0.45), rgba(13,17,23,0.26))",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
      }}
    >
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <h3 style={{ margin: 0, fontSize: 13, color: "#9fc7ff", fontWeight: 700, letterSpacing: 0.45 }}>
          Analytics Dashboard
        </h3>
        <span style={{ fontSize: 11, color: "#9aa5b1" }}>{graph.order.toLocaleString()} nodes</span>
      </header>

      <div style={sectionWrapStyle}>
        <button
          type="button"
          onClick={() => setCentralityOpen((value) => !value)}
          style={sectionHeaderStyle}
        >
          <span>Centrality Rankings</span>
          <span style={{ color: "#8b949e" }}>{isCentralityOpen ? "−" : "+"}</span>
        </button>

        <div style={sectionBodyStyle(isCentralityOpen)}>
          <div style={{ display: "flex", gap: 8, paddingBottom: 8 }}>
            <button
              type="button"
              onClick={() => setRankingMode("degree")}
              style={memoizedPillStyle(rankingMode === "degree")}
            >
              Degree
            </button>
            <button
              type="button"
              onClick={() => setRankingMode("importance")}
              style={memoizedPillStyle(rankingMode === "importance")}
            >
              Importance
            </button>
          </div>

          {rankedNodes.length === 0 ? (
            <div style={emptyStateStyle}>No ranked nodes available.</div>
          ) : (
            rankedNodes.map((node, index) => (
              <button
                key={node.id}
                type="button"
                onClick={() => onSelectNode(node.id)}
                onMouseEnter={() => setHoveredNodeId(node.id)}
                onMouseLeave={() => setHoveredNodeId(null)}
                style={memoizedRowButtonStyle(hoveredNodeId === node.id)}
                title={node.id}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ color: "#58a6ff", fontSize: 11, width: 24 }}>#{index + 1}</span>
                  <span style={{ color: "#e6edf3", fontSize: 12, fontWeight: 600, flex: 1, textAlign: "left" }}>
                    {node.label}
                  </span>
                  <span style={{ color: "#8b949e", fontSize: 11 }}>
                    {rankingMode === "degree" ? node.degree : node.importance.toFixed(3)}
                  </span>
                </div>
                <div style={{ color: "#8b949e", fontSize: 11, textAlign: "left", marginTop: 2 }}>
                  {node.type}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      <div style={{ ...sectionWrapStyle, marginTop: 12 }}>
        <button
          type="button"
          onClick={() => setClustersOpen((value) => !value)}
          style={sectionHeaderStyle}
        >
          <span>Community Clusters</span>
          <span style={{ color: "#8b949e" }}>{isClustersOpen ? "−" : "+"}</span>
        </button>

        <div style={sectionBodyStyle(isClustersOpen)}>
          <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 8 }}>
            {model.totalClusters.toLocaleString()} total clusters
          </div>

          {model.clusters.length === 0 ? (
            <div style={emptyStateStyle}>No cluster metadata found in node properties.</div>
          ) : (
            model.clusters.map((cluster) => {
              const isActive = isolatedClusterId === cluster.id;

              return (
                <button
                  key={cluster.id}
                  type="button"
                  onClick={() => {
                    const nextCluster = isActive ? null : cluster.id;
                    onIsolateCluster(nextCluster);
                    if (nextCluster) {
                      onSelectNode(cluster.sampleNodeId);
                    }
                  }}
                  onMouseEnter={() => setHoveredClusterId(cluster.id)}
                  onMouseLeave={() => setHoveredClusterId(null)}
                  style={{
                    ...memoizedRowButtonStyle(hoveredClusterId === cluster.id),
                    borderColor: isActive ? "rgba(116,176,255,0.48)" : "rgba(255,255,255,0.1)",
                    background: isActive
                      ? "linear-gradient(135deg, rgba(53,121,221,0.28), rgba(24,74,143,0.18))"
                      : hoveredClusterId === cluster.id
                        ? "rgba(255,255,255,0.07)"
                        : "rgba(255,255,255,0.03)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ color: "#e6edf3", fontSize: 12, fontWeight: 600, textAlign: "left", flex: 1 }}>
                      {cluster.id}
                    </span>
                    <span style={{ color: "#58a6ff", fontSize: 11 }}>{cluster.size.toLocaleString()}</span>
                  </div>
                  <div style={{ color: "#8b949e", fontSize: 11, marginTop: 2, textAlign: "left" }}>
                    {isActive ? "Click to show all clusters" : "Click to isolate cluster"}
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>
    </section>
  );
}

const sectionWrapStyle: React.CSSProperties = {
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.1)",
  background: "linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05)",
  backdropFilter: "blur(10px)",
  WebkitBackdropFilter: "blur(10px)",
  overflow: "hidden",
};

const sectionHeaderStyle: React.CSSProperties = {
  width: "100%",
  border: "none",
  background: "rgba(255,255,255,0.04)",
  color: "#e6edf3",
  padding: "10px 12px",
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: 0.35,
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  cursor: "pointer",
  transition: "background 150ms ease",
};

const sectionBodyStyle = (open: boolean): React.CSSProperties => ({
  maxHeight: open ? 360 : 0,
  opacity: open ? 1 : 0,
  transition: "max-height 220ms ease, opacity 180ms ease",
  overflowY: "auto",
  padding: open ? "10px" : "0 10px",
});

const emptyStateStyle: React.CSSProperties = {
  color: "#8b949e",
  fontSize: 12,
  padding: "10px 4px",
};
