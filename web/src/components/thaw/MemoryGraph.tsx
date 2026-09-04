"use client";

import { useCallback, useEffect } from "react";
import {
  Background, BackgroundVariant, Handle, Position, ReactFlow,
  useEdgesState, useNodesState, type Edge, type Node,
} from "@xyflow/react";
import { Brain } from "lucide-react";
import { FlowEdge } from "./FlowEdge";
import { API } from "@/lib/thaw";

type Learning = { test_id: string; claim: string };

function toneOf(claim: string) {
  if (/WINS/i.test(claim)) return "var(--pos)";
  if (/HURT/i.test(claim)) return "var(--harm)";
  if (/wash|no difference/i.test(claim)) return "var(--muted-foreground)";
  return "var(--notice)";
}

function CenterNode({ data }: { data: { count: number } }) {
  return (
    <div className="relative grid h-[104px] w-[104px] place-items-center rounded-full border border-[color:var(--brand2)] bg-[radial-gradient(circle_at_30%_30%,color-mix(in_oklch,var(--brand)_45%,transparent),var(--card))]"
      style={{ boxShadow: "0 0 60px -10px var(--brand)" }}>
      <Handle type="source" position={Position.Right} className="!opacity-0" />
      <Brain className="h-7 w-7 text-white" />
      <div className="mt-1 text-[11px] font-semibold text-white">Memory</div>
      <div className="mono text-[10px] text-[color:var(--brand2)]">{data.count} learned</div>
    </div>
  );
}
function CardNode({ data }: { data: { claim: string; tone: string } }) {
  return (
    <div className="w-[210px] rounded-xl border px-3 py-2.5 glass" style={{ borderColor: `color-mix(in oklch, ${data.tone} 45%, transparent)`, boxShadow: `0 8px 30px -16px ${data.tone}` }}>
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

  const load = useCallback(async () => {
    try {
      const d: { learnings: Learning[] } = await (await fetch(API + "/memory")).json();
      const seen = new Set<string>();
      const items = d.learnings.filter((l) => (seen.has(l.claim) ? false : (seen.add(l.claim), true))).slice(0, 8);
      const center: Node = { id: "center", type: "memcenter", position: { x: 0, y: 0 }, data: { count: items.length }, draggable: false };
      // wide-short container: fan the claims to the right of the hub so nothing overflows vertically
      const RX = 430, RY = 165;
      const n = Math.max(1, items.length);
      const cards: Node[] = items.map((l, i) => {
        const a = n === 1 ? 0 : (-1 + (2 * i) / (n - 1)) * (Math.PI * 0.48); // right hemisphere, cos stays > 0
        return { id: `m${i}`, type: "memcard", position: { x: Math.cos(a) * RX, y: Math.sin(a) * RY }, data: { claim: l.claim, tone: toneOf(l.claim) }, draggable: false };
      });
      const es: Edge[] = items.map((_, i) => ({ id: `e${i}`, source: "center", target: `m${i}`, type: "flow", data: { live: true } }));
      setNodes([center, ...cards]); setEdges(es);
    } catch { /* backend offline */ }
  }, [setNodes, setEdges]);

  useEffect(() => { load(); }, [load, nonce]);

  return (
    // fixed layout + fixed 380px-tall container → a deterministic viewport frames the fan reliably
    // (fitView races the async node load and mis-frames the wide-short canvas)
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes}
      defaultViewport={{ x: 190, y: 190, zoom: 0.7 }} proOptions={{ hideAttribution: true }}
      nodesConnectable={false} elementsSelectable={false} zoomOnScroll={false} panOnScroll minZoom={0.3} maxZoom={1.2}>
      <Background variant={BackgroundVariant.Dots} gap={30} size={1} color="color-mix(in oklch, var(--brand) 40%, transparent)" />
    </ReactFlow>
  );
}
