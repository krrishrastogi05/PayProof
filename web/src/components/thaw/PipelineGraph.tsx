"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background, BackgroundVariant, ReactFlow,
  useEdgesState, useNodesState, type Edge, type Node, type ReactFlowInstance,
} from "@xyflow/react";
import { StageNode, SubNode, type StageData } from "./StageNode";
import { FlowEdge } from "./FlowEdge";
import { rupee, STAGE_OF, STAGE_ORDER, type ThawEvent } from "@/lib/thaw";

const MY = 100, SY = 280;
const POS: Record<string, number> = { watcher: 0, reasoner: 270, rules: 540, feasibility: 810, runner: 1080, scoreboard: 1350, memory: 1620 };
const stage = (id: string, label: string, sub: string): Node<StageData> =>
  ({ id, type: "stage", position: { x: POS[id], y: MY }, data: { label, sub, state: "idle", stage: id } });
const sub = (id: string, x: number, label: string, s?: string): Node =>
  ({ id, type: "sub", position: { x, y: SY }, data: { label, sub: s, on: false } });

const INIT_NODES: Node[] = [
  stage("watcher", "Watcher", "flags a slipped slice"),
  stage("reasoner", "Reasoner", "Gemini proposes"),
  stage("rules", "Rules", "allowed? · policy.yaml"),
  stage("feasibility", "Feasibility", "can we measure it?"),
  stage("runner", "Runner", "split · run · brake"),
  stage("scoreboard", "Scoreboard", "sequential test"),
  stage("memory", "Memory", "what we learned"),
  sub("gemini", 205, "Gemini", "gemini-3.6-flash"),
  sub("recall", 400, "Ledger recall", "what happened before"),
  sub("policy", 850, "policy.yaml", "the boundaries"),
  sub("simulator", 1055, "Simulator", "seeded traffic"),
  sub("brake", 1255, "Brake", "cap + stop rules"),
];

const edge = (a: string, b: string, sub = false): Edge =>
  ({ id: `${a}-${b}`, source: a, target: b, type: "flow", sourceHandle: sub ? "b" : undefined, data: { live: false } });
const INIT_EDGES: Edge[] = [
  edge("watcher", "reasoner"), edge("reasoner", "rules"), edge("rules", "feasibility"),
  edge("feasibility", "runner"), edge("runner", "scoreboard"), edge("scoreboard", "memory"),
  edge("reasoner", "gemini", true), edge("reasoner", "recall", true),
  edge("feasibility", "policy", true), edge("runner", "simulator", true), edge("runner", "brake", true),
];

function detailFor(e: ThawEvent): { detail?: string; tone?: string } {
  const n = (k: string) => e[k] as number;
  switch (e.kind) {
    case "TOO_SMALL": return { detail: `${Math.round(n("needed_days"))}d needed › ${n("max_days")}d limit`, tone: "var(--notice)" };
    case "CAP_SET": return { detail: `cap ${rupee(n("max_loss_inr"))}`, tone: "var(--brand2)" };
    case "BLOCKED": return { detail: "blocked by policy", tone: "var(--harm)" };
    case "RUNNING": return { detail: `${rupee(n("realized_loss_inr") || 0)} / ${rupee(n("max_loss_inr") || 0)}`, tone: "var(--cyan)" };
    case "KEPT": return { detail: `+${n("uplift_pp")}pp · kept`, tone: "var(--pos)" };
    case "NO_DIFFERENCE": return { detail: "range spans 0 · no diff", tone: "var(--muted-foreground)" };
    case "BRAKE_PULLED": return { detail: "BRAKE PULLED", tone: "var(--harm)" };
    case "LEARNED": return { detail: "written to memory", tone: "var(--violet)" };
    case "PROPOSED": return { detail: e.proposed_by === "gemini" ? "Gemini ✓" : "local fallback", tone: "var(--violet)" };
    case "THINKING": return { detail: `recall ${e.history ?? 0} results`, tone: "var(--violet)" };
    case "RECALLED": return { detail: n("seen") > 0 ? `memory: ${e.verdict}` : "memory checked", tone: "var(--cyan)" };
    case "SKIPPED_BY_MEMORY": return { detail: "skipped · already known", tone: "var(--cyan)" };
    default: return {};
  }
}

const nodeTypes = { stage: StageNode, sub: SubNode };
const edgeTypes = { flow: FlowEdge };

export function PipelineGraph({ event, running }: { event: ThawEvent | null; running: boolean }) {
  const [nodes, setNodes] = useNodesState<Node<StageData>>(INIT_NODES as Node<StageData>[]);
  const [edges, setEdges] = useEdgesState<Edge>(INIT_EDGES);
  const [ready, setReady] = useState(false);
  const rf = useRef<ReactFlowInstance<Node<StageData>, Edge> | null>(null);

  useEffect(() => {
    if (!event) { setNodes(INIT_NODES.map((n) => ({ ...n, data: { ...(n.data as StageData) } })) as Node<StageData>[]); setEdges(INIT_EDGES.map((e) => ({ ...e, data: { live: false } }))); return; }
    const sId = STAGE_OF[event.kind]; if (!sId) return;
    const idx = STAGE_ORDER.indexOf(sId);
    const { detail, tone } = detailFor(event);
    const subsOn = new Set<string>();
    if (sId === "reasoner") { subsOn.add("recall"); if (event.kind !== "RECALLED") subsOn.add("gemini"); }
    if (sId === "feasibility") subsOn.add("policy");
    if (sId === "runner") { subsOn.add("simulator"); if (event.kind === "BRAKE_PULLED") subsOn.add("brake"); }

    setNodes((nds) => nds.map((nd) => {
      if (nd.type === "sub") return { ...nd, data: { ...nd.data, on: subsOn.has(nd.id) } };
      const i = STAGE_ORDER.indexOf(nd.id);
      const state: StageData["state"] = i === idx ? "active" : i < idx ? "done" : nd.data.state === "done" ? "done" : "idle";
      return { ...nd, data: { ...nd.data, state, detail: i === idx ? (detail ?? nd.data.detail) : nd.data.detail, tone: i === idx ? tone : nd.data.tone } };
    }));
    setEdges((eds) => eds.map((ed) => ({ ...ed, data: { live: STAGE_ORDER.indexOf(ed.target) === idx || subsOn.has(ed.target) } })));

    // cinematic camera: follow the active stage
    rf.current?.setCenter(POS[sId] + 118, MY + 120, { zoom: 0.92, duration: 650 });
  }, [event, setNodes, setEdges]);

  useEffect(() => {
    if (!running) rf.current?.fitView({ padding: 0.16, duration: 700 });
  }, [running]);

  const onInit = useCallback((inst: ReactFlowInstance<Node<StageData>, Edge>) => {
    rf.current = inst; inst.fitView({ padding: 0.16 });
  }, []);
  // paint the dot pattern only after the flow has measured its box (avoids NaN SVG)
  useEffect(() => { const t = setTimeout(() => setReady(true), 60); return () => clearTimeout(t); }, []);
  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  return (
    <ReactFlow
      nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} onInit={onInit}
      fitView fitViewOptions={{ padding: 0.16 }} proOptions={proOptions}
      nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}
      panOnScroll zoomOnScroll={false} panOnDrag minZoom={0.4} maxZoom={1.3}
    >
      {ready && <Background variant={BackgroundVariant.Dots} gap={30} size={1.2} color="color-mix(in oklch, var(--brand) 45%, transparent)" />}
    </ReactFlow>
  );
}
