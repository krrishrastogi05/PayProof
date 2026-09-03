"use client";

import { BaseEdge, getBezierPath, type EdgeProps } from "@xyflow/react";

export function FlowEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data }: EdgeProps) {
  const [path] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, curvature: 0.35 });
  const live = Boolean((data as { live?: boolean } | undefined)?.live);
  const stroke = live ? "var(--brand2)" : "var(--brand)";
  return (
    <>
      <BaseEdge id={id} path={path} style={{ stroke, strokeOpacity: live ? 0.85 : 0.22, strokeWidth: live ? 2.4 : 1.4 }} />
      <circle r={live ? 3.4 : 2.2} fill={stroke} opacity={live ? 1 : 0.45}
        style={live ? { filter: "drop-shadow(0 0 5px var(--brand2))" } : undefined}>
        <animateMotion dur={live ? "1.1s" : "2.6s"} repeatCount="indefinite" path={path} />
      </circle>
      {live && (
        <circle r={2.6} fill="var(--brand2)" opacity={0.7}>
          <animateMotion dur="1.1s" begin="0.55s" repeatCount="indefinite" path={path} />
        </circle>
      )}
    </>
  );
}
