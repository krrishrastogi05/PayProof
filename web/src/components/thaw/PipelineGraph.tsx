"use client";

import { useCallback, useEffect, useMemo } from "react";
import {
  Background, BackgroundVariant, Controls, ReactFlow,
  useEdgesState, useNodesState, type Edge, type Node,
} from "@xyflow/react";
import { StageNode, SubNode, type StageData } from "./StageNode";
import { rupee, STAGE_OF, STAGE_ORDER, type ThawEvent } from "@/lib/thaw";

const stage = (id: string, x: number, label: string, sub: string): Node<StageData> => ({
  id, type: "stage", position: { x, y: 70 },
  data: { label, sub, state: "idle", stage: id },
});
const sub = (id: string, x: number, y: number, label: string, s?: string): Node =>
  ({ id, type: "sub", position: { x, y }, data: { label, sub: s, on: false } });

const INIT_NODES: Node[] = [
  stage("watcher", 0, "Watcher", "flags a slipped slice"),
  stage("reasoner", 250, "Reasoner", "Gemini proposes"),
  stage("rules", 500, "Rules", "allowed? policy.yaml"),
  stage("feasibility", 750, "Feasibility", "can we measure it?"),
  stage("runner", 1000, "Runner", "split · run · brake"),
  stage("scoreboard", 1250, "Scoreboard", "sequential test"),
  stage("memory", 1500, "Memory", "what we learned"),
  sub("gemini", 250, 210, "Gemini", "gemini-3.6-flash"),
  sub("recall", 420, 210, "Ledger recall", "what happened before"),
  sub("policy", 750, 210, "policy.yaml", "the boundaries"),
  sub("simulator", 980, 210, "Simulator", "seeded traffic"),
  sub("brake", 1150, 210, "Brake", "cap + stop rules"),
];

const mainEdge = (a: string, b: string): Edge =>
  ({ id: `${a}-${b}`, source: a, target: b, animated: true, className: "animated" });
const subEdge = (a: string, b: string): Edge =>
  ({ id: `${a}-${b}`, source: a, sourceHandle: "b", target: b, className: "animated", animated: true });

const INIT_EDGES: Edge[] = [
  mainEdge("watcher", "reasoner"), mainEdge("reasoner", "rules"), mainEdge("rules", "feasibility"),
  mainEdge("feasibility", "runner"), mainEdge("runner", "scoreboard"), mainEdge("scoreboard", "memory"),
  subEdge("reasoner", "gemini"), subEdge("reasoner", "recall"),
  subEdge("feasibility", "policy"), subEdge("runner", "simulator"), subEdge("runner", "brake"),
];

function detailFor(e: ThawEvent): { detail?: string; tone?: string } {
  const n = (k: string) => e[k] as number;
  switch (e.kind) {
    case "TOO_SMALL": return { detail: `${Math.round(n("needed_days"))}d > ${n("max_days")}d limit`, tone: "var(--notice)" };
    case "CAP_SET": return { detail: `cap ${rupee(n("max_loss_inr"))}`, tone: "var(--brand2)" };
    case "BLOCKED": return { detail: "blocked", tone: "var(--harm)" };
    case "RUNNING": return { detail: `${rupee(n("realized_loss_inr") || 0)} / ${rupee(n("max_loss_inr") || 0)}`, tone: "var(--cyan)" };
    case "KEPT": return { detail: `+${n("uplift_pp")}pp · kept`, tone: "var(--pos)" };
    case "NO_DIFFERENCE": return { detail: "≈0 · no difference", tone: "var(--muted-foreground)" };
    case "BRAKE_PULLED": return { detail: "BRAKE PULLED", tone: "var(--harm)" };
    case "LEARNED": return { detail: "learned ✓", tone: "var(--violet)" };
    case "PROPOSED": return { detail: e.proposed_by === "gemini" ? "Gemini ✓" : "local", tone: "var(--violet)" };
    case "THINKING": return { detail: `recall ${e.history ?? 0}`, tone: "var(--violet)" };
    default: return {};
  }
}

const nodeTypes = { stage: StageNode, sub: SubNode };

export function PipelineGraph({ event }: { event: ThawEvent | null }) {
  const [nodes, setNodes] = useNodesState<Node<StageData>>(INIT_NODES as Node<StageData>[]);
  const [edges, setEdges] = useEdgesState<Edge>(INIT_EDGES);

  useEffect(() => {
    if (!event) return;
    const sId = STAGE_OF[event.kind];
    if (!sId) return;
    const idx = STAGE_ORDER.indexOf(sId);
    const { detail, tone } = detailFor(event);
    const subsOn = new Set<string>();
    if (sId === "reasoner") { subsOn.add("gemini"); subsOn.add("recall"); }
    if (sId === "feasibility") subsOn.add("policy");
    if (sId === "runner") { subsOn.add("simulator"); if (event.kind === "BRAKE_PULLED") subsOn.add("brake"); }

    setNodes((nds) => nds.map((nd) => {
      if (nd.type === "sub") return { ...nd, data: { ...nd.data, on: subsOn.has(nd.id) } };
      const i = STAGE_ORDER.indexOf(nd.id);
      const state: StageData["state"] = i === idx ? "active" : i < idx ? "done" : nd.data.state === "done" ? "done" : "idle";
      const keepDetail = i === idx ? (detail ?? nd.data.detail) : nd.data.detail;
      const keepTone = i === idx ? tone : nd.data.tone;
      return { ...nd, data: { ...nd.data, state, detail: keepDetail, tone: keepTone } };
    }));

    setEdges((eds) => eds.map((ed) => {
      const live = STAGE_ORDER.indexOf(ed.target) === idx || (subsOn.has(ed.target));
      return { ...ed, className: live ? "animated live" : "animated" };
    }));
  }, [event, setNodes, setEdges]);

  const reset = useCallback(() => {
    setNodes(INIT_NODES.map((n) => ({ ...n, data: { ...(n.data as object) } })) as Node<StageData>[]);
    setEdges(INIT_EDGES.map((e) => ({ ...e })));
  }, [setNodes, setEdges]);
  useEffect(() => { if (event === null) reset(); }, [event, reset]);

  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes} edges={edges} nodeTypes={nodeTypes}
        fitView fitViewOptions={{ padding: 0.15 }} proOptions={proOptions}
        nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}
        panOnScroll zoomOnScroll={false} minZoom={0.4} maxZoom={1.4}
      >
        <Background variant={BackgroundVariant.Dots} gap={26} size={1} color="var(--brand)" />
        <Controls showInteractive={false} className="!bg-card !border-border" />
      </ReactFlow>
    </div>
  );
}
