"use client";

import { Handle, Position } from "@xyflow/react";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { Eye, Sparkles, ShieldCheck, Ruler, FlaskConical, Scale, Brain, Check } from "lucide-react";

const ICON: Record<string, LucideIcon> = {
  watcher: Eye, reasoner: Sparkles, rules: ShieldCheck, feasibility: Ruler,
  runner: FlaskConical, scoreboard: Scale, memory: Brain,
};

export type StageData = {
  label: string; sub: string; state: "idle" | "active" | "done";
  detail?: string; tone?: string; stage: string;
};

const H = "!h-2 !w-2 !border-2 !border-[color:var(--background)] !bg-[color:var(--brand)]";

export function StageNode({ data }: { data: StageData }) {
  const Icon = ICON[data.stage] ?? Eye;
  const active = data.state === "active";
  const done = data.state === "done";
  const tone = data.tone ?? "var(--brand2)";
  const accent = active ? tone : done ? "var(--brand)" : "var(--muted-foreground)";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0, scale: active ? 1.03 : 1 }}
      transition={{ type: "spring", stiffness: 260, damping: 22 }}
      className="relative w-[236px] overflow-hidden rounded-[18px] border"
      style={{
        borderColor: active ? tone : "var(--border)",
        background: "linear-gradient(180deg, color-mix(in oklch, var(--card) 92%, white 5%), var(--card))",
        boxShadow: active
          ? `0 0 0 1px ${tone}, 0 16px 44px -14px color-mix(in oklch, ${tone} 55%, transparent), 0 0 30px -8px color-mix(in oklch, ${tone} 40%, transparent)`
          : done ? "0 12px 30px -16px rgba(30,54,110,.28)" : "0 10px 26px -16px rgba(30,54,110,.2)",
        opacity: data.state === "idle" ? 0.8 : 1,
      }}
    >
      <div className="h-[3px] w-full" style={{ background: `linear-gradient(90deg, ${accent}, transparent)` }} />
      <Handle type="target" position={Position.Left} className={H} />
      <div className="flex items-start gap-3 px-4 pb-3.5 pt-3">
        <span className="relative grid h-10 w-10 shrink-0 place-items-center rounded-xl"
          style={{
            background: active ? `linear-gradient(140deg, ${tone}, color-mix(in oklch, ${tone} 55%, black))` : "color-mix(in oklch, var(--brand) 14%, transparent)",
            color: active ? "#fff" : "var(--brand2)",
            boxShadow: active ? `0 6px 16px -6px ${tone}` : undefined,
          }}>
          <Icon className="h-[18px] w-[18px]" />
          {done && !active && (
            <span className="absolute -right-1 -top-1 grid h-4 w-4 place-items-center rounded-full bg-[color:var(--pos)] text-black">
              <Check className="h-2.5 w-2.5" strokeWidth={3} />
            </span>
          )}
        </span>
        <div className="min-w-0 pt-0.5">
          <div className="text-[14px] font-semibold leading-tight text-foreground">{data.label}</div>
          <div className="mt-0.5 text-[11px] leading-tight text-muted-foreground">{data.sub}</div>
        </div>
      </div>
      {data.detail && (
        <div className="mx-4 mb-3.5 flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5"
          style={{ borderColor: `color-mix(in oklch, ${accent} 30%, transparent)`, background: `color-mix(in oklch, ${accent} 12%, transparent)` }}>
          {active && <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: tone, boxShadow: `0 0 6px ${tone}` }} />}
          <span className="mono truncate text-[11.5px] font-medium" style={{ color: accent }}>{data.detail}</span>
        </div>
      )}
      <Handle type="source" position={Position.Right} className={H} />
      <Handle type="source" position={Position.Bottom} id="b" className="!opacity-0" />
    </motion.div>
  );
}

export function SubNode({ data }: { data: { label: string; sub?: string; on?: boolean } }) {
  return (
    <motion.div animate={{ opacity: data.on ? 1 : 0.5 }}
      className="w-[164px] rounded-[14px] border px-3 py-2.5"
      style={{
        borderColor: data.on ? "var(--brand2)" : "var(--border)",
        background: "var(--card)",
        boxShadow: data.on ? "0 10px 26px -12px color-mix(in oklch, var(--brand) 55%, transparent)" : "0 8px 20px -14px rgba(30,54,110,.2)",
      }}>
      <Handle type="target" position={Position.Top} className={H} />
      <div className="flex items-center gap-2">
        {data.on && <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--brand2)]" style={{ boxShadow: "0 0 6px var(--brand2)" }} />}
        <div className="text-[12.5px] font-medium text-foreground">{data.label}</div>
      </div>
      {data.sub && <div className="mono mt-0.5 text-[10px] text-muted-foreground">{data.sub}</div>}
    </motion.div>
  );
}
