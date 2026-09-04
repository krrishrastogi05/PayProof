"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, TrendingDown, Brain, AlertTriangle, Check, Radar } from "lucide-react";
import { API, rupee } from "@/lib/thaw";

type Evidence = {
  fp_naive: number; fp_sequential: number;
  cap_tests: number; cap_broken: number;
  cold_tests: number; cold_loss: number;
  experienced_tests: number; experienced_loss: number;
};
type Pattern = {
  slice: string; family: string; verdict: string; stability: string; seeds: number;
  discovered_pp: number; true_pp: number; match: boolean;
};
const pp = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(1)}pp`;
const vTone = (v: string) => v === "WINS" ? "var(--pos)" : v === "HURT" ? "var(--harm)" : "var(--muted-foreground)";

function Bar({ pct, tone, label, value }: { pct: number; tone: string; label: string; value: string }) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-[12px]">
        <span className="text-muted-foreground">{label}</span>
        <span className="mono font-semibold" style={{ color: tone }}>{value}</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-white/5">
        <motion.div className="h-full rounded-full" style={{ background: tone }}
          initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.9, ease: "easeOut" }} />
      </div>
    </div>
  );
}

function Card({ icon: Icon, eyebrow, children }: { icon: typeof Brain; eyebrow: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border glass p-4">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 text-[color:var(--brand2)]" /><span className="eyebrow">{eyebrow}</span>
      </div>
      {children}
    </div>
  );
}

function PatternPanel({ pats }: { pats: Pattern[] | null }) {
  const hit = pats ? pats.filter((p) => p.match).length : 0;
  return (
    <div className="rounded-xl border border-border glass p-4">
      <div className="mb-1 flex items-center gap-2">
        <Radar className="h-3.5 w-3.5 text-[color:var(--brand2)]" /><span className="eyebrow">Patterns the agent extracted — scored against the hidden truth it never saw</span>
        {pats && <span className="ml-auto mono text-[12px] font-semibold text-[color:var(--pos)]">{hit}/{pats.length} recovered</span>}
      </div>
      <div className="mb-3 text-[12px] text-muted-foreground">Each slice run across seeds; the verdict is the agent&apos;s own, from noisy observations. Truth is revealed only to score.</div>
      {!pats ? (
        <div className="flex items-center gap-2 py-4 text-[13px] text-muted-foreground"><div className="h-4 w-4 animate-spin rounded-full border-2 border-white/15 border-t-[color:var(--brand)]" /> running the agent across seeds…</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] border-collapse text-[12.5px]">
            <thead>
              <tr className="text-[11px] uppercase tracking-wide text-muted-foreground">
                <th className="py-1.5 text-left font-medium">slice</th>
                <th className="text-left font-medium">lever</th>
                <th className="text-left font-medium">discovered</th>
                <th className="text-left font-medium">stability</th>
                <th className="text-left font-medium">truth</th>
                <th className="text-right font-medium">match</th>
              </tr>
            </thead>
            <tbody className="mono">
              {pats.map((p, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="py-2 text-foreground">{p.slice}</td>
                  <td className="text-muted-foreground">{p.family}</td>
                  <td><span className="font-semibold" style={{ color: vTone(p.verdict) }}>{p.verdict}</span> <span className="text-muted-foreground">{pp(p.discovered_pp)}</span></td>
                  <td className="text-muted-foreground">{p.stability}</td>
                  <td className="text-muted-foreground">{pp(p.true_pp)}</td>
                  <td className="text-right">{p.match
                    ? <span className="inline-flex items-center gap-1 text-[color:var(--pos)]"><Check className="h-3.5 w-3.5" />matched</span>
                    : <span className="text-[color:var(--harm)]">missed</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function ProofView() {
  const [d, setD] = useState<Evidence | null>(null);
  const [pats, setPats] = useState<Pattern[] | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let on = true;
    fetch(API + "/evidence").then((r) => r.json()).then((j) => on && setD(j)).catch(() => on && setErr(true));
    fetch(API + "/patterns").then((r) => r.json()).then((j) => on && setPats(j)).catch(() => {});
    return () => { on = false; };
  }, []);

  if (err) return <div className="grid h-full place-items-center text-[13px] text-muted-foreground">couldn&apos;t reach the backend at {API}</div>;

  return (
    <div className="h-full overflow-auto p-5">
      <div className="mx-auto max-w-[860px] space-y-4">
        {/* the demonstration: patterns recovered vs the hidden truth */}
        <PatternPanel pats={pats} />
        {!d ? (
          <div className="flex items-center gap-2 rounded-xl border border-border glass p-4 text-[13px] text-muted-foreground">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/15 border-t-[color:var(--brand)]" /> measuring on the real simulator — 200 trials, 40 tests…
          </div>
        ) : (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* the headline credibility number */}
        <Card icon={AlertTriangle} eyebrow="Would a naive A/B be safe?">
          <div className="mb-3 text-[13px] leading-relaxed text-muted-foreground">
            Across <span className="text-foreground">200 trials where the change truly does nothing</span>, how often does each method
            declare a false winner and ship it?
          </div>
          <div className="space-y-3">
            <Bar pct={d.fp_naive} tone="var(--harm)" label="Naive A/B (peek & ship)" value={`${d.fp_naive}%`} />
            <Bar pct={d.fp_sequential} tone="var(--pos)" label="PayProof (sequential test)" value={`${d.fp_sequential}%`} />
          </div>
          <div className="mt-3 text-[12px] text-muted-foreground">
            Same data, same peeking. PayProof&apos;s sequential boundary is <span className="text-foreground">~{Math.round(d.fp_naive / d.fp_sequential)}× less likely</span> to ship a phantom win.
          </div>
        </Card>

        {/* memory compounding */}
        <Card icon={Brain} eyebrow="Does memory compound?">
          <div className="mb-3 text-[13px] leading-relaxed text-muted-foreground">
            The same slices, run by a <span className="text-foreground">cold</span> agent vs. one that <span className="text-foreground">remembers</span> what already failed.
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-border bg-black/20 p-3">
              <div className="text-[11px] text-muted-foreground">Cold start</div>
              <div className="mono mt-1 text-[22px] font-semibold">{d.cold_tests.toFixed(0)}<span className="text-[13px] text-muted-foreground"> tests</span></div>
              <div className="mono text-[13px] text-[color:var(--harm)]">{rupee(d.cold_loss)} at risk</div>
            </div>
            <div className="rounded-lg border border-[color:var(--pos)]/25 bg-[color:var(--pos)]/5 p-3">
              <div className="text-[11px] text-muted-foreground">With memory</div>
              <div className="mono mt-1 text-[22px] font-semibold">{d.experienced_tests.toFixed(0)}<span className="text-[13px] text-muted-foreground"> test</span></div>
              <div className="mono text-[13px] text-[color:var(--pos)]">{rupee(d.experienced_loss)} at risk</div>
            </div>
          </div>
          <div className="mt-3 text-[12px] text-muted-foreground">
            It skips what it already learned hurts — fewer tests, less money exposed, every re-run.
          </div>
        </Card>

        {/* the cap held */}
        <Card icon={ShieldCheck} eyebrow="Did the spending cap ever break?">
          <div className="flex items-center gap-4">
            <div className="mono text-[40px] font-semibold text-[color:var(--pos)]">{d.cap_broken}</div>
            <div className="text-[13px] leading-relaxed text-muted-foreground">
              cap breaches across <span className="text-foreground">{d.cap_tests} tests</span> / 20 seeds.
              The brake checks every 40 sessions, so realized loss can never jump the rupee cap.
            </div>
          </div>
        </Card>

        {/* the thesis */}
        <Card icon={TrendingDown} eyebrow="Why it matters">
          <div className="text-[13px] leading-relaxed text-muted-foreground">
            A frozen setting is a silent, unbounded bet. PayProof turns it into a <span className="text-foreground">bounded experiment</span>:
            weak evidence stops a test, strong evidence promotes it, an independent brake caps the downside in rupees —
            and every number here traces to the ledger, not a slide.
          </div>
        </Card>
      </div>
        )}
      </div>
    </div>
  );
}
