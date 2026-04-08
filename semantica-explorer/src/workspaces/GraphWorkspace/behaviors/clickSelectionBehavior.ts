import type { GraphBehavior } from "./types";

export const clickSelectionBehavior: GraphBehavior = {
  id: "click-selection",
  attach: () => {},
  detach: () => {},
  onNodeClick: (context, nodeId) => {
    context.setHoveredNodeId(nodeId);
    context.onNodeSelectionChange(nodeId);
  },
  onStageClick: (context) => {
    context.setHoveredNodeId(null);
    context.onNodeSelectionChange("");
  },
};
