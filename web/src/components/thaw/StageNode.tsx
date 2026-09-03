"use client";

import { Handle, Position } from "@xyflow/react";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import {
  Eye, Sparkles, ShieldCheck, Ruler, FlaskConical, Scale, Brain,
} from "lucide-react";

const ICON: Record<string, LucideIcon> = {
  watcher: Eye, reasoner: Sparkles, rules: ShieldCheck, feasibility: Ruler,
  runner: FlaskConical, scoreboard: Scale, memory: Brain,
};

export type StageData = {
  label: string;
  sub: string;
  state: "idle" | "active" | "done";
  detail?: string;
  tone?: string; // css color for detail/border when meaningful
  stage: string;
};

export function StageNode({ data }: { data: StageData }) {
  const Icon = ICON[data.stage] ?? Eye;
  const active = data.state === "active";
  const done = data.state === "done";
  const tone = data.tone;
  const border = active ? "border-[color:var(--brand2)]" : done ? "border-[color:var(--brand)]/40" : "border-border";
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className={`w-[190px] rounded-2xl border ${border} glass px-3.5 py-3 shadow-lg ${active ? "pulsering" : ""}`}
      style={active && tone ? { borderColor: tone } : undefined}
    >
      <Handle type="target" position={Position.Left} className="!bg-[color:var(--brand)] !border-0 !w-1.5 !h-1.5" />
      <div className="flex items-center gap-2.5">
        <span
          className="grid h-8 w-8 place-items-center rounded-lg"
          style={{
            background: active ? (tone ?? "var(--brand)") : "color-mix(in oklch, var(--brand) 16%, transparent)",
            color: active ? "#fff" : "var(--brand2)",
          }}
        >
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <div className="text-[13px] font-semibold leading-tight text-foreground">{data.label}</div>
          <div className="text-[10.5px] text-muted-foreground leading-tight">{data.sub}</div>
        </div>
      </div>
      {data.detail && (
        <div className="mono mt-2 rounded-md bg-black/20 px-2 py-1 text-[11px]" style={{ color: tone ?? "var(--foreground)" }}>
          {data.detail}
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-[color:var(--brand)] !border-0 !w-1.5 !h-1.5" />
      <Handle type="target" position={Position.Top} id="t" className="!opacity-0" />
      <Handle type="source" position={Position.Bottom} id="b" className="!opacity-0" />
    </motion.div>
  );
}

export function SubNode({ data }: { data: { label: string; sub?: string; on?: boolean } }) {
  return (
    <div className={`w-[150px] rounded-xl border px-3 py-2 glass ${data.on ? "border-[color:var(--brand2)]" : "border-border"}`}>
      <Handle type="target" position={Position.Top} className="!bg-[color:var(--brand)] !border-0 !w-1.5 !h-1.5" />
      <div className="text-[12px] font-medium text-foreground">{data.label}</div>
      {data.sub && <div className="text-[10px] text-muted-foreground mono">{data.sub}</div>}
    </div>
  );
}
