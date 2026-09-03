"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Zap, Terminal as TermIcon, Radio } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PipelineGraph } from "@/components/thaw/PipelineGraph";
import { Terminal } from "@/components/thaw/Terminal";
import { openStream, rupee, type ThawEvent } from "@/lib/thaw";

const KIND_TONE: Record<string, string> = {
  WATCHING: "var(--muted-foreground)", THINKING: "var(--violet)", PROPOSED: "var(--violet)",
  BLOCKED: "var(--harm)", TOO_SMALL: "var(--notice)", CAP_SET: "var(--brand2)",
  RUNNING: "var(--cyan)", BRAKE_PULLED: "var(--harm)", KEPT: "var(--pos)",
  NO_DIFFERENCE: "var(--muted-foreground)", REVERTED: "var(--notice)", LEARNED: "var(--violet)",
};
const label = (k: string) => k.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

export default function Home() {
  const [started, setStarted] = useState(false);
  const [running, setRunning] = useState(false);
  const [live, setLive] = useState(false);
  const [event, setEvent] = useState<ThawEvent | null>(null);
  const [feed, setFeed] = useState<ThawEvent[]>([]);
  const [active, setActive] = useState<{ head: string; loss: number; cap: number; rc?: number; rt?: number } | null>(null);
  const [simTs, setSimTs] = useState(0);
  const t0 = useRef(Date.now());
  const [real, setReal] = useState("0:00");
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const i = setInterval(() => { const s = Math.floor((Date.now() - t0.current) / 1000); setReal(`${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`); }, 1000);
    return () => clearInterval(i);
  }, []);

  const onEvent = useCallback((e: ThawEvent) => {
    setEvent(e); setSimTs((e.sim_ts as number) || 0);
    setFeed((f) => [e, ...f].slice(0, 10));
    if (e.kind === "CAP_SET") setActive({ head: String(e.note || ""), loss: 0, cap: (e.max_loss_inr as number) || 0 });
    if (e.kind === "RUNNING" && e.day) setActive({ head: String(e.headline || "running"), loss: (e.realized_loss_inr as number) || 0, cap: (e.max_loss_inr as number) || 1, rc: (e.rate_control as number) * 100, rt: (e.rate_treatment as number) * 100 });
  }, []);

  const start = useCallback((liveRun: boolean) => {
    esRef.current?.close();
    setStarted(true); setRunning(true); setLive(liveRun);
    setEvent(null); setFeed([]); setActive(null); t0.current = Date.now();
    setTimeout(() => { esRef.current = openStream(liveRun, onEvent, () => setRunning(false)); }, 60);
  }, [onEvent]);

  const fmtSim = (s: number) => `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h`;
  const tone = event ? KIND_TONE[event.kind] || "var(--foreground)" : "var(--foreground)";

  return (
    <div className="relative z-10 mx-auto flex min-h-screen max-w-[1280px] flex-col px-6">
      {/* header */}
      <header className="sticky top-0 z-30 -mx-6 mb-2 flex items-center gap-4 border-b border-border glass px-6 py-3.5">
        <div className="flex items-baseline gap-1 text-[19px] font-semibold tracking-tight">
          Thaw<span className="font-serif-em text-[color:var(--gold)]">.</span>
        </div>
        <span className="border-l border-border pl-4 text-[13px] text-muted-foreground">Acme Electronics</span>
        <div className="ml-auto flex items-center gap-4 text-[12px]">
          <span className="mono"><span className="text-muted-foreground">SIM </span>{fmtSim(simTs)}</span>
          <span className="mono"><span className="text-muted-foreground">REAL </span>{real}</span>
          <span className="mono text-muted-foreground">10,000×</span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--brand)]/25 bg-[color:var(--accent)] px-2.5 py-1 text-[11px] font-semibold text-[color:var(--accent-foreground)]">
            <Radio className="h-3 w-3" /> {running ? "RUNNING" : "CANARY"}
          </span>
        </div>
      </header>

      {/* hero */}
      {!started && (
        <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="py-14">
          <div className="eyebrow mb-3">The frozen setting</div>
          <h1 className="max-w-[16ch] text-[52px] font-semibold leading-[1.02] tracking-[-.03em]">
            UPI shown first on mobile. <span className="font-serif-em text-[color:var(--gold)]">Still.</span>
          </h1>
          <div className="mt-4 text-[13px] text-muted-foreground">Set <span className="text-[color:var(--notice)]">19 months ago</span> · never re-tested · nobody has looked since.</div>
          <p className="mt-5 max-w-[54ch] text-[16px] leading-relaxed text-muted-foreground">
            Every merchant&apos;s payment settings are a frozen guess. Thaw un-freezes them — with a rules engine,
            a spending cap, and an emergency brake, and an honest record of <span className="font-serif-em text-[color:var(--gold)]">what didn&apos;t work.</span>
          </p>
          <div className="mt-7 flex items-center gap-3">
            <Button size="lg" onClick={() => start(false)} className="gap-2"><Zap className="h-4 w-4" /> Un-freeze it</Button>
            <label className="flex cursor-pointer items-center gap-2 text-[13px] text-muted-foreground">
              <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} className="accent-[color:var(--brand)]" /> Live · Gemini
            </label>
            <Button size="lg" variant="ghost" onClick={() => start(live)}>with the terminal ↓</Button>
          </div>
        </motion.section>
      )}

      {/* graph */}
      <motion.section layout className={`rounded-2xl border border-border glass ${started ? "mt-2 h-[440px]" : "mt-6 h-[340px]"} overflow-hidden`}>
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <span className="eyebrow">The pipeline · live</span>
          <span className="text-[11px] text-muted-foreground">{running ? "processing…" : started ? "run complete" : "idle"}</span>
        </div>
        <div className="h-[calc(100%-42px)]"><PipelineGraph event={event} /></div>
      </motion.section>

      {/* terminal + signal */}
      <section className="my-4 grid grid-cols-1 gap-4 pb-16 lg:grid-cols-[1.35fr_1fr]">
        <div className="h-[320px]"><Terminal onRun={start} /></div>
        <div className="flex flex-col gap-4">
          {/* latest signal */}
          <div className="rounded-xl border border-border glass p-4">
            <div className="flex items-center gap-2"><TermIcon className="h-3.5 w-3.5 text-muted-foreground" /><span className="eyebrow">Latest signal</span></div>
            {event ? (
              <motion.div key={event.seq} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="mt-3">
                <div className="text-[15px] font-semibold" style={{ color: tone }}>{label(event.kind)}</div>
                <div className="mt-1 text-[13px] text-muted-foreground">
                  {String(event.reason || event.note || event.headline || event.claim || event.slice || "")}
                </div>
              </motion.div>
            ) : <div className="mt-3 text-[13px] text-muted-foreground">Run the pipeline to see the agent think.</div>}
          </div>
          {/* money at risk */}
          <div className="rounded-xl border border-border glass p-4">
            <span className="eyebrow">Money at risk</span>
            <div className="mt-2 mono text-[26px] font-semibold" style={{ color: active && active.loss > 0 ? "var(--harm)" : "var(--foreground)" }}>
              {rupee(active?.loss ?? 0)} <span className="text-[15px] text-muted-foreground">/ {rupee(active?.cap ?? 0)}</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/5">
              <div className="h-full rounded-full transition-all duration-500" style={{ width: `${active ? Math.min(100, (active.loss / (active.cap || 1)) * 100) : 0}%`, background: active && active.loss / (active.cap || 1) > 0.5 ? "var(--harm)" : "var(--brand)" }} />
            </div>
            {active?.rc != null && (
              <div className="mt-3 space-y-1 text-[12px]">
                <div className="flex justify-between"><span className="text-muted-foreground">control</span><span className="mono">{active.rc.toFixed(1)}%</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">cards-first</span><span className="mono">{active.rt?.toFixed(1)}%</span></div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
