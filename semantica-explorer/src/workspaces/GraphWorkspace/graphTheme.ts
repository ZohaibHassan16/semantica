export type GraphZoomTier = "overview" | "structure" | "inspection";
export type GraphNodeVisualState = "default" | "hovered" | "selected" | "neighbor" | "path" | "inactive" | "muted";
export type GraphEdgeVisualState = "default" | "hovered" | "selected" | "neighbor" | "path" | "inactive" | "muted";

export interface GraphTheme {
  palette: {
    semantic: string[];
    accent: {
      selected: string;
      hovered: string;
      path: string;
    };
    muted: {
      fallback: string;
      nodeAlpha: number;
      edgeOverview: string;
      edgeStructure: string;
      edgeInspection: string;
      edgeFocus: string;
    };
    background: {
      canvas: string;
      shell: string;
      shellBorder: string;
      shellGlow: string;
      grid: string;
      vignette: string;
      nodeBorder: string;
    };
  };
  zoomTiers: Record<GraphZoomTier, {
    maxRatio: number;
    nodeScale: number;
    labelThreshold: number;
    labelBudget: number;
    edgePriorityThreshold: number;
    arrowPriorityThreshold: number;
    edgeSizeScale: number;
  }>;
  labels: {
    forceVisibleStates: readonly GraphNodeVisualState[];
  };
  nodes: {
    backgroundScale: number;
    mutedAlpha: number;
    states: Record<GraphNodeVisualState, {
      color: "base" | "selected" | "hovered" | "path" | "muted";
      sizeMultiplier: number;
      minSize: number;
      forceLabel: boolean;
      zIndex: number;
    }>;
  };
  edges: {
    states: Record<GraphEdgeVisualState, {
      color: "overview" | "structure" | "inspection" | "hover" | "path" | "focus" | "muted";
      sizeMultiplier: number;
      minSize: number;
      zIndex: number;
      forceArrow: boolean;
      hide: boolean;
    }>;
  };
  overlays: {
    hoverGlowAlpha: number;
    pathGlowAlpha: number;
    glowRadiusMultiplier: number;
    minGlowRadius: number;
    pulseRadius: number;
  };
  focus: {
    maxNeighbors: number;
    ringCapacity: number;
    ringGap: number;
    primaryLabels: number;
  };
  motion: {
    cameraMs: number;
  };
}

export const GRAPH_THEME: GraphTheme = {
  palette: {
    semantic: [
      "#63E6FF",
      "#30D4C7",
      "#72A8FF",
      "#8D7CFF",
      "#C07CFF",
      "#FF67D4",
      "#FFB24D",
      "#C5F55A",
    ],
    accent: {
      selected: "#FFC857",
      hovered: "#7FE0FF",
      path: "#FFB870",
    },
    muted: {
      fallback: "rgba(130, 145, 165, 0.12)",
      nodeAlpha: 0.12,
      edgeOverview: "rgba(116, 166, 255, 0.05)",
      edgeStructure: "rgba(109, 164, 255, 0.11)",
      edgeInspection: "rgba(146, 194, 255, 0.18)",
      edgeFocus: "rgba(162, 184, 255, 0.34)",
    },
    background: {
      canvas: "#060B17",
      shell: "rgba(6, 13, 24, 0.76)",
      shellBorder: "rgba(112, 196, 255, 0.14)",
      shellGlow: "rgba(53, 123, 255, 0.16)",
      grid: "rgba(88, 166, 255, 0.038)",
      vignette: "rgba(1, 4, 10, 0.82)",
      nodeBorder: "#07111C",
    },
  },
  zoomTiers: {
    overview: {
      maxRatio: Number.POSITIVE_INFINITY,
      nodeScale: 0.9,
      labelThreshold: 0.985,
      labelBudget: 18,
      edgePriorityThreshold: 0.72,
      arrowPriorityThreshold: Number.POSITIVE_INFINITY,
      edgeSizeScale: 0.72,
    },
    structure: {
      maxRatio: 1.2,
      nodeScale: 0.98,
      labelThreshold: 0.88,
      labelBudget: 36,
      edgePriorityThreshold: 0.4,
      arrowPriorityThreshold: 0.75,
      edgeSizeScale: 0.92,
    },
    inspection: {
      maxRatio: 0.5,
      nodeScale: 1,
      labelThreshold: 0.7,
      labelBudget: 80,
      edgePriorityThreshold: 0,
      arrowPriorityThreshold: 0.58,
      edgeSizeScale: 1.04,
    },
  },
  labels: {
    forceVisibleStates: ["hovered", "selected", "neighbor", "path"],
  },
  nodes: {
    backgroundScale: 0.52,
    mutedAlpha: 0.12,
    states: {
      default: { color: "base", sizeMultiplier: 1, minSize: 1.45, forceLabel: false, zIndex: 0 },
      hovered: { color: "hovered", sizeMultiplier: 1.34, minSize: 16, forceLabel: true, zIndex: 4 },
      selected: { color: "selected", sizeMultiplier: 1.18, minSize: 12, forceLabel: true, zIndex: 3 },
      neighbor: { color: "base", sizeMultiplier: 1.08, minSize: 7.2, forceLabel: true, zIndex: 2 },
      path: { color: "path", sizeMultiplier: 1.08, minSize: 7.2, forceLabel: true, zIndex: 2 },
      inactive: { color: "muted", sizeMultiplier: 0.52, minSize: 0.8, forceLabel: false, zIndex: 0 },
      muted: { color: "muted", sizeMultiplier: 0.52, minSize: 0.8, forceLabel: false, zIndex: 0 },
    },
  },
  edges: {
    states: {
      default: { color: "inspection", sizeMultiplier: 1, minSize: 0.72, zIndex: 0, forceArrow: false, hide: false },
      hovered: { color: "hover", sizeMultiplier: 1.55, minSize: 1.8, zIndex: 3, forceArrow: true, hide: false },
      selected: { color: "hover", sizeMultiplier: 1.55, minSize: 1.8, zIndex: 3, forceArrow: true, hide: false },
      neighbor: { color: "focus", sizeMultiplier: 1.08, minSize: 0.95, zIndex: 1, forceArrow: false, hide: false },
      path: { color: "path", sizeMultiplier: 1.7, minSize: 2.2, zIndex: 4, forceArrow: true, hide: false },
      inactive: { color: "muted", sizeMultiplier: 1, minSize: 0.45, zIndex: 0, forceArrow: false, hide: true },
      muted: { color: "muted", sizeMultiplier: 1, minSize: 0.45, zIndex: 0, forceArrow: false, hide: true },
    },
  },
  overlays: {
    hoverGlowAlpha: 0.26,
    pathGlowAlpha: 0.2,
    glowRadiusMultiplier: 4.8,
    minGlowRadius: 16,
    pulseRadius: 11,
  },
  focus: {
    maxNeighbors: 16,
    ringCapacity: 6,
    ringGap: 250,
    primaryLabels: 6,
  },
  motion: {
    cameraMs: 380,
  },
};

export function hashString(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(index);
    hash |= 0;
  }
  return Math.abs(hash);
}

export function clamp(min: number, value: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function withAlpha(color: string | undefined, alpha: number): string {
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

export function darkenHex(hexColor: string, amount: number): string {
  if (!hexColor.startsWith("#")) {
    return hexColor;
  }

  const hex = hexColor.slice(1);
  const normalized = hex.length === 3
    ? hex.split("").map((char) => `${char}${char}`).join("")
    : hex;

  if (normalized.length !== 6) {
    return hexColor;
  }

  const clampChannel = (value: number) => clamp(0, value, 255);
  const red = clampChannel(Number.parseInt(normalized.slice(0, 2), 16) - amount);
  const green = clampChannel(Number.parseInt(normalized.slice(2, 4), 16) - amount);
  const blue = clampChannel(Number.parseInt(normalized.slice(4, 6), 16) - amount);

  return `#${[red, green, blue].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

export function getZoomTier(ratio: number): GraphZoomTier {
  if (ratio <= GRAPH_THEME.zoomTiers.inspection.maxRatio) {
    return "inspection";
  }
  if (ratio <= GRAPH_THEME.zoomTiers.structure.maxRatio) {
    return "structure";
  }
  return "overview";
}
