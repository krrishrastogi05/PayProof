"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Zap, Terminal as TermIcon, Radio, Workflow, CreditCard, Brain, BarChart3, History, ShieldAlert, OctagonX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PipelineGraph } from "@/components/thaw/PipelineGraph";
import { Terminal } from "@/components/thaw/Terminal";
import { CheckoutAB, RetryAB } from "@/components/thaw/Checkout";
import { MemoryGraph } from "@/components/thaw/MemoryGraph";
import { ProofView } from "@/components/thaw/ProofView";
import { RunsView } from "@/components/thaw/RunsView";
import { openStream, rupee, type ThawEvent } from "@/lib/thaw";

const KIND_TONE: Record<string, string> = {
  WATCHING: "var(--muted-foreground)", THINKING: "var(--violet)", PROPOSED: "var(--violet)",
  BLOCKED: "var(--harm)", TOO_SMALL: "var(--notice)", CAP_SET: "var(--brand2)",
  RUNNING: "var(--cyan)", BRAKE_PULLED: "var(--harm)", KEPT: "var(--pos)",
  NO_DIFFERENCE: "var(--muted-foreground)", REVERTED: "var(--notice)", LEARNED: "var(--violet)",
};
const label = (k: string) => k.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

type View = "pipeline" | "checkout" | "memory" | "runs" | "proof";
const VIEWS: { id: View; label: string; icon: typeof Workflow }[] = [
  { id: "pipeline", label: "Pipeline", icon: Workflow },
  { id: "checkout", label: "Checkout", icon: CreditCard },
  { id: "memory", label: "Memory", icon: Brain },
  { id: "runs", label: "Runs", icon: History },
  { id: "proof", label: "Proof", icon: BarChart3 },
];

export default function Home() {
  const [started, setStarted] = useState(false);
  const [running, setRunning] = useState(false);
  const [live, setLive] = useState(false);
  const [view, setView] = useState<View>("pipeline");
  const [event, setEvent] = useState<ThawEvent | null>(null);
  const [active, setActive] = useState<{ head: string; loss: number; cap: number; rc?: number; rt?: number } | null>(null);
  const [simTs, setSimTs] = useState(0);
  const [memNonce, setMemNonce] = useState(0);
  const [testKind, setTestKind] = useState("payment_method_order");
  const t0 = useRef(Date.now());
  const [real, setReal] = useState("0:00");
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const i = setInterval(() => { const s = Math.floor((Date.now() - t0.current) / 1000); setReal(`${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`); }, 1000);
    return () => clearInterval(i);
  }, []);

  const onEvent = useCallback((e: ThawEvent) => {
    setEvent(e); setSimTs((e.sim_ts as number) || 0);
    if (e.test_kind) setTestKind(String(e.test_kind));
    if (e.kind === "CAP_SET") setActive({ head: String(e.note || ""), loss: 0, cap: (e.max_loss_inr as number) || 0 });
    if (e.kind === "RUNNING" && e.day) setActive({ head: String(e.headline || "running"), loss: (e.realized_loss_inr as number) || 0, cap: (e.max_loss_inr as number) || 1, rc: (e.rate_control as number) * 100, rt: (e.rate_treatment as number) * 100 });
    if (e.kind === "BRAKE_PULLED") setActive((a) => (a ? { ...a, loss: (e.realized_loss_inr as number) ?? a.loss, cap: (e.max_loss_inr as number) ?? a.cap } : a));
    // pull the operator's eye to the surface that just changed: the whole test
    // lifecycle plays out on the checkout; a blocked idea stays on the pipeline.
    const toCheckout = new Set(["CAP_SET", "RUNNING", "KEPT", "BRAKE_PULLED", "REVERTED", "NO_DIFFERENCE"]);
    if (toCheckout.has(e.kind)) setView("checkout");
  }, []);

  const start = useCallback((liveRun: boolean, seed = 42) => {
    esRef.current?.close();
    setStarted(true); setRunning(true); setLive(liveRun);
    setEvent(null); setActive(null); setView("pipeline"); setTestKind("payment_method_order"); t0.current = Date.now();
    setTimeout(() => {
      esRef.current = openStream(liveRun, seed, onEvent, () => { setRunning(false); setMemNonce((n) => n + 1); setView("memory"); });
    }, 60);
  }, [onEvent]);

  const fmtSim = (s: number) => `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h`;
  const tone = event ? KIND_TONE[event.kind] || "var(--foreground)" : "var(--foreground)";
  const pct = active ? Math.min(100, (active.loss / (active.cap || 1)) * 100) : 0;
  const braked = event?.kind === "BRAKE_PULLED";

  return (
    <div className="relative z-10 mx-auto flex h-screen w-full max-w-[1600px] flex-col overflow-hidden px-5">
      {/* header — brand, clocks, run controls */}
      <header className="flex shrink-0 items-center gap-4 border-b border-border py-3">
        <div className="flex items-baseline gap-1 text-[19px] font-semibold tracking-tight">
          Thaw<span className="font-serif-em text-[color:var(--gold)]">.</span>
        </div>
        <span className="hidden border-l border-border pl-4 text-[13px] text-muted-foreground sm:inline">Acme Electronics</span>
        <span className="hidden text-[12px] text-muted-foreground md:inline">· UPI shown first on mobile, set 19 months ago, never re-tested</span>
        <div className="ml-auto flex items-center gap-4 text-[12px]">
          <span className="mono hidden sm:inline"><span className="text-muted-foreground">SIM </span>{fmtSim(simTs)}</span>
          <span className="mono hidden sm:inline"><span className="text-muted-foreground">REAL </span>{real}</span>
          <span className="mono hidden text-muted-foreground lg:inline">10,000×</span>
          <label className="hidden cursor-pointer items-center gap-1.5 text-[12px] text-muted-foreground sm:flex">
            <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} disabled={running} className="accent-[color:var(--brand)]" /> Gemini
          </label>
          <Button size="sm" onClick={() => start(live)} disabled={running} className="gap-1.5">
            <Zap className="h-3.5 w-3.5" /> {running ? "Running…" : started ? "Re-run" : "Un-freeze it"}
          </Button>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--brand)]/25 bg-[color:var(--accent)] px-2.5 py-1 text-[11px] font-semibold text-[color:var(--accent-foreground)]">
            <Radio className="h-3 w-3" /> {running ? "RUNNING" : "CANARY"}
          </span>
        </div>
      </header>

      {/* cockpit — canvas + inspector rail, one screen, no scroll */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 py-3 lg:grid-cols-[minmax(0,1fr)_360px]">
        {/* canvas */}
        <section className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-border glass">
          <div className="flex shrink-0 items-center justify-between border-b border-border px-3 py-2">
            <div className="flex items-center gap-1 rounded-lg border border-border bg-black/20 p-0.5">
              {VIEWS.map((v) => {
                const on = view === v.id;
                return (
                  <button key={v.id} onClick={() => setView(v.id)}
                    className={`relative inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors ${on ? "text-[color:var(--accent-foreground)]" : "text-muted-foreground hover:text-foreground"}`}>
                    {on && <motion.span layoutId="viewpill" className="absolute inset-0 rounded-md bg-[color:var(--accent)]" transition={{ type: "spring", stiffness: 400, damping: 32 }} />}
                    <v.icon className="relative z-10 h-3.5 w-3.5" /><span className="relative z-10">{v.label}</span>
                  </button>
                );
              })}
            </div>
            <span className="pr-1 text-[11px] text-muted-foreground">
              {view === "pipeline" ? (running ? "processing…" : started ? "run complete" : "idle")
                : view === "checkout" ? "the frozen setting, tested live"
                  : view === "memory" ? "what survived the tests"
                    : view === "runs" ? "every run archived & reported"
                      : "measured on the real simulator"}
            </span>
          </div>
          <div className="relative min-h-0 flex-1">
            {/* all three layers stay mounted (opacity toggle, not unmount) so React Flow measures
                the canvas once at load and never re-races fitView on a tab switch */}
            <div className={`absolute inset-0 transition-opacity duration-200 ${view === "pipeline" ? "" : "pointer-events-none opacity-0"}`}>
              <PipelineGraph event={event} running={running} />
            </div>
            <div className={`absolute inset-0 overflow-auto p-5 transition-opacity duration-200 ${view === "checkout" ? "" : "pointer-events-none opacity-0"}`}>
              {testKind === "retry_timing"
                ? <RetryAB event={event} rc={active?.rc} rt={active?.rt} />
                : <CheckoutAB event={event} rc={active?.rc} rt={active?.rt} />}
            </div>
            <div className={`absolute inset-0 transition-opacity duration-200 ${view === "memory" ? "" : "pointer-events-none opacity-0"}`}>
              <MemoryGraph nonce={memNonce} />
            </div>
            {view === "runs" && <div className="absolute inset-0"><RunsView nonce={memNonce} /></div>}
            {view === "proof" && <div className="absolute inset-0"><ProofView /></div>}
          </div>
        </section>

        {/* inspector rail */}
        <aside className="flex min-h-0 flex-col gap-3">
          {/* latest signal — with a distinct spotlight for the two safety beats */}
          {event?.kind === "BLOCKED" ? (
            <motion.div key={event.seq} initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}
              className="shrink-0 rounded-xl border border-[color:var(--harm)]/40 bg-[color:var(--harm)]/8 p-4">
              <div className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-[color:var(--harm)]" /><span className="eyebrow text-[color:var(--harm)]">Refused · rules engine</span></div>
              <div className="mt-2 text-[15px] font-semibold text-[color:var(--harm)]">Blocked before any spend</div>
              <div className="mt-1 text-[13px] text-muted-foreground">{String(event.reason || event.headline || "")}</div>
              {Array.isArray(event.touches) && (event.touches as string[]).length > 0 && (
                <div className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-[color:var(--harm)]/30 bg-black/20 px-2 py-1 text-[11px] mono text-[color:var(--harm)]">
                  <OctagonX className="h-3 w-3" /> {(event.touches as string[]).join(" · ")}
                </div>
              )}
            </motion.div>
          ) : (
            <div className="shrink-0 rounded-xl border border-border glass p-4">
              <div className="flex items-center gap-2"><TermIcon className="h-3.5 w-3.5 text-muted-foreground" /><span className="eyebrow">Latest signal</span></div>
              {event ? (
                <motion.div key={event.seq} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} className="mt-2.5">
                  <div className="text-[15px] font-semibold" style={{ color: tone }}>{label(event.kind)}</div>
                  <div className="mt-1 line-clamp-2 text-[13px] text-muted-foreground">
                    {String(event.reason || event.note || event.headline || event.claim || event.slice || "")}
                  </div>
                </motion.div>
              ) : <div className="mt-2.5 text-[13px] text-muted-foreground">Press <span className="text-foreground">Un-freeze it</span> to watch the agent think.</div>}
            </div>
          )}

          {/* money at risk — flips to the brake beat when the cap defends the merchant */}
          <motion.div animate={braked ? { boxShadow: ["0 0 0 0 rgba(255,91,86,0)", "0 0 0 3px rgba(255,91,86,.35)", "0 0 0 0 rgba(255,91,86,0)"] } : {}}
            transition={{ duration: 0.9, repeat: braked ? 1 : 0 }}
            className={`shrink-0 rounded-xl border p-4 ${braked ? "border-[color:var(--harm)]/40 bg-[color:var(--harm)]/8" : "border-border glass"}`}>
            <div className="flex items-center justify-between">
              <span className="eyebrow">Money at risk</span>
              {braked && <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[color:var(--harm)]"><OctagonX className="h-3 w-3" /> BRAKE FIRED</span>}
            </div>
            <div className="mt-2 mono text-[24px] font-semibold" style={{ color: active && active.loss > 0 ? "var(--harm)" : "var(--foreground)" }}>
              {rupee(active?.loss ?? 0)} <span className="text-[14px] text-muted-foreground">/ {rupee(active?.cap ?? 0)} cap</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/5">
              <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: pct > 50 || braked ? "var(--harm)" : "var(--brand)" }} />
            </div>
            {braked ? (
              <div className="mt-2.5 text-[12px] text-muted-foreground">Halted at <span className="text-[color:var(--harm)]">{rupee(active?.loss ?? 0)}</span> — the cap allowed up to {rupee(active?.cap ?? 0)}. Reverted to UPI-first.</div>
            ) : active?.rc != null && (
              <div className="mt-3 space-y-1 text-[12px]">
                <div className="flex justify-between"><span className="text-muted-foreground">control · UPI first</span><span className="mono">{active.rc.toFixed(1)}%</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">cards first</span><span className="mono">{active.rt?.toFixed(1)}%</span></div>
              </div>
            )}
          </motion.div>

          {/* terminal — always available */}
          <div className="min-h-0 flex-1"><Terminal onRun={start} /></div>
        </aside>
      </div>
    </div>
  );
}
