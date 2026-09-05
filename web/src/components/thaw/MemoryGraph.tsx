"use client";

import { useCallback, useEffect, useRef } from "react";
import {
  Handle, Position, ReactFlow,
  useEdgesState, useNodesState, type Edge, type Node, type ReactFlowInstance,
} from "@xyflow/react";
import { Brain } from "lucide-react";
import { FlowEdge } from "./FlowEdge";
import { API } from "@/lib/thaw";

// CSS dot texture instead of React Flow's <Background>, which computes NaN when the
// container is briefly 0-sized; this never can.
const DOTS = {
  backgroundImage: "radial-gradient(color-mix(in oklch, var(--brand) 22%, transparent) 1px, transparent 1px)",
  backgroundSize: "30px 30px",
} as const;

type Learning = { test_id: string; claim: string; verdict?: string };

const toneOf = (v?: string) => v === "win" ? "var(--pos)" : v === "harm" ? "var(--harm)" : "var(--muted-foreground)";

function CenterNode({ data }: { data: { count: number } }) {
  return (
    <div className="relative grid h-[108px] w-[108px] place-items-center rounded-full text-white"
      style={{ background: "linear-gradient(145deg, var(--brand), var(--brand2))", boxShadow: "0 18px 50px -12px color-mix(in oklch, var(--brand) 60%, transparent)" }}>
      <Handle type="source" position={Position.Right} className="!opacity-0" />
      <Brain className="h-7 w-7" strokeWidth={2.2} />
      <div className="mt-1 text-[11px] font-semibold">Memory</div>
      <div className="mono text-[10px] text-white/85">{data.count} learned</div>
    </div>
  );
}
function CardNode({ data }: { data: { claim: string; tone: string } }) {
  return (
    <div className="w-[250px] rounded-xl border bg-card px-3.5 py-3" style={{ borderColor: `color-mix(in oklch, ${data.tone} 40%, transparent)`, boxShadow: `0 10px 34px -14px color-mix(in oklch, ${data.tone} 55%, transparent)` }}>
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <div className="flex items-start gap-2">
        <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: data.tone, boxShadow: `0 0 8px ${data.tone}` }} />
        <div className="text-[12px] leading-snug text-foreground">{data.claim}</div>
      </div>
    </div>
  );
}
const nodeTypes = { memcenter: CenterNode, memcard: CardNode };
const edgeTypes = { flow: FlowEdge };

export function MemoryGraph({ nonce }: { nonce: number }) {
  const [nodes, setNodes] = useNodesState<Node>([]);
  const [edges, setEdges] = useEdgesState<Edge>([]);
  const rf = useRef<ReactFlowInstance<Node, Edge> | null>(null);

  const load = useCallback(async () => {
    try {
      const d: { learnings: Learning[] } = await (await fetch(API + "/memory")).json();
      const seen = new Set<string>();
      const items = d.learnings.filter((l) => (seen.has(l.claim) ? false : (seen.add(l.claim), true))).slice(0, 8);
      const center: Node = { id: "center", type: "memcenter", position: { x: 0, y: 0 }, data: { count: items.length }, draggable: false };
      const R = 340;
      const n = Math.max(1, items.length);
      const cards: Node[] = items.map((l, i) => {
        const a = (i / n) * Math.PI * 2 - Math.PI / 2; // full circle around the hub
        return { id: `m${i}`, type: "memcard", position: { x: Math.cos(a) * R, y: Math.sin(a) * R }, data: { claim: l.claim, tone: toneOf(l.verdict) }, draggable: false };
      });
      const es: Edge[] = items.map((_, i) => ({ id: `e${i}`, source: "center", target: `m${i}`, type: "flow", data: { live: true } }));
      setNodes([center, ...cards]); setEdges(es);
    } catch { /* backend offline */ }
  }, [setNodes, setEdges]);

  useEffect(() => { load(); }, [load, nonce]);
  // nodes arrive after the async fetch AND React Flow measures their sizes a tick later,
  // so rAF is too early — a short timeout lets fitView frame the real bounding box.
  useEffect(() => {
    if (!nodes.length) return;
    const t = setTimeout(() => rf.current?.fitView({ padding: 0.22, duration: 400 }), 220);
    return () => clearTimeout(t);
  }, [nodes.length]);

  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes}
      onInit={(i) => { rf.current = i; }} style={DOTS}
      fitView fitViewOptions={{ padding: 0.22 }} proOptions={{ hideAttribution: true }}
      nodesConnectable={false} elementsSelectable={false} zoomOnScroll={false} panOnScroll minZoom={0.3} maxZoom={1.2} />
  );
}
