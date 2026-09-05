"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { History, FileText, Trophy, OctagonX, ShieldAlert, Minus } from "lucide-react";
import { API, getJSON, rupee } from "@/lib/thaw";

type Run = {
  id: number; run_id: string; seed: number; live: number; created_at: string; policy_json: string;
  n_tests: number; n_winners: number; n_harmful: number; n_wash: number;
  n_blocked: number; n_learnings: number; total_loss_inr: number; cap_broken: number; sim_seconds: number;
};
type Learning = { claim: string; verdict?: string };
type Report = {
  run: Run; levers: Record<string, number | string>;
  learnings: Learning[]; blocked: string[];
};

const toneOf = (v?: string) => v === "win" ? "var(--pos)" : v === "harm" ? "var(--harm)" : "var(--muted-foreground)";

function Chip({ icon: Icon, label, value, tone }: { icon: typeof Trophy; label: string; value: number | string; tone: string }) {
  return (
    <div className="flex items-center gap-1.5 rounded-lg border border-border bg-[color:var(--secondary)] px-2.5 py-1.5">
      <Icon className="h-3.5 w-3.5" style={{ color: tone }} />
      <span className="mono text-[13px] font-semibold" style={{ color: tone }}>{value}</span>
      <span className="text-[11px] text-muted-foreground">{label}</span>
    </div>
  );
}

export function RunsView({ nonce }: { nonce: number }) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [sel, setSel] = useState<number | null>(null);
  const [rep, setRep] = useState<Report | null>(null);

  const load = useCallback(async () => {
    try {
      const rs = await getJSON<Run[]>("/runs");
      setRuns(rs);
      setSel((s) => s ?? (rs[0]?.id ?? null));
    } catch { /* backend offline */ }
  }, []);
  useEffect(() => { load(); }, [load, nonce]);
  useEffect(() => {
    if (sel == null) { setRep(null); return; }
    let on = true;
    getJSON<Report>(`/runs/${sel}/report`).then((r) => on && setRep(r)).catch(() => {});
    return () => { on = false; };
  }, [sel]);

  if (!runs.length) return (
    <div className="grid h-full place-items-center text-[13px] text-muted-foreground">
      No runs archived yet — run <span className="mx-1 text-foreground">simulate</span> to start the history.
    </div>
  );

  return (
    <div className="grid h-full grid-cols-1 gap-3 overflow-hidden p-4 md:grid-cols-[300px_minmax(0,1fr)]">
      {/* run history list */}
      <div className="flex min-h-0 flex-col">
        <div className="mb-2 flex items-center gap-2"><History className="h-3.5 w-3.5 text-[color:var(--brand2)]" /><span className="eyebrow">Run history</span><span className="ml-auto mono text-[11px] text-muted-foreground">{runs.length}</span></div>
        <div className="min-h-0 flex-1 space-y-2 overflow-auto pr-1">
          {runs.map((r) => {
            const lev = JSON.parse(r.policy_json || "{}");
            const on = r.id === sel;
            return (
              <button key={r.id} onClick={() => setSel(r.id)}
                className={`w-full rounded-xl border p-3 text-left transition-all ${on ? "border-[color:var(--brand)]/50 bg-[color:var(--accent)]" : "border-border glass hover:-translate-y-0.5 hover:border-[color:var(--brand)]/30"}`}>
                <div className="flex items-center justify-between">
                  <span className="mono text-[13px] font-semibold">#{r.id} <span className="text-muted-foreground">seed {r.seed}</span></span>
                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{r.live ? "live" : "curated"}</span>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1.5 text-[11px]">
                  <span className="mono text-[color:var(--pos)]">{r.n_winners} kept</span>
                  <span className="mono text-[color:var(--harm)]">{r.n_harmful} braked</span>
                  <span className="mono text-[color:var(--notice)]">{r.n_blocked} blocked</span>
                </div>
                <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
                  <span className="mono">{rupee(r.total_loss_inr)} exposed</span>
                  <span className="mono">traffic {lev.max_traffic_share ?? "—"}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* report for the selected run */}
      <div className="flex min-h-0 flex-col rounded-xl border border-border glass">
        <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2.5"><FileText className="h-3.5 w-3.5 text-[color:var(--brand2)]" /><span className="eyebrow">Run report</span>{rep && <span className="ml-auto mono text-[11px] text-muted-foreground">{rep.run.created_at.replace("T", " ").replace("+00:00", " UTC")}</span>}</div>
        {rep ? (
          <motion.div key={rep.run.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="min-h-0 flex-1 overflow-auto p-4">
            <div className="mb-1 text-[17px] font-semibold">{rep.run.run_id} · seed {rep.run.seed}</div>
            <div className="mb-3 text-[12px] text-muted-foreground">{rep.run.live ? "live · Gemini" : "curated"} · sim horizon {(rep.run.sim_seconds / 86400).toFixed(1)}d</div>

            <div className="mb-4 flex flex-wrap gap-2">
              <Chip icon={Trophy} label="kept" value={rep.run.n_winners} tone="var(--pos)" />
              <Chip icon={OctagonX} label="braked" value={rep.run.n_harmful} tone="var(--harm)" />
              <Chip icon={Minus} label="wash" value={rep.run.n_wash} tone="var(--muted-foreground)" />
              <Chip icon={ShieldAlert} label="blocked" value={rep.run.n_blocked} tone="var(--notice)" />
              <Chip icon={OctagonX} label="cap breaches" value={rep.run.cap_broken} tone={rep.run.cap_broken ? "var(--harm)" : "var(--pos)"} />
            </div>

            <div className="mb-3">
              <div className="eyebrow mb-1.5">Policy levers</div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(rep.levers).map(([k, v]) => (
                  <span key={k} className="mono rounded-md border border-border bg-[color:var(--secondary)] px-2 py-1 text-[11px]"><span className="text-muted-foreground">{k}</span> {String(v)}</span>
                ))}
              </div>
            </div>

            <div className="mb-3">
              <div className="eyebrow mb-1.5">What the agent learned</div>
              <div className="space-y-1.5">
                {rep.learnings.length ? rep.learnings.map((l, i) => (
                  <div key={i} className="flex items-start gap-2 text-[12.5px]">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: toneOf(l.verdict) }} />
                    <span className="text-foreground">{l.claim}</span>
                  </div>
                )) : <div className="text-[12px] text-muted-foreground">nothing concluded yet</div>}
              </div>
            </div>

            {rep.blocked.length > 0 && (
              <div>
                <div className="eyebrow mb-1.5">Refused before any spend</div>
                <div className="space-y-1">
                  {rep.blocked.map((b, i) => (
                    <div key={i} className="flex items-start gap-2 text-[12.5px] text-muted-foreground"><ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--harm)]" />{b}</div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        ) : <div className="grid flex-1 place-items-center text-[13px] text-muted-foreground">select a run</div>}
      </div>
    </div>
  );
}
