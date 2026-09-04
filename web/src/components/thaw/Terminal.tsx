"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { API, getJSON, rupee } from "@/lib/thaw";

type Line = { id: number; node: ReactNode };
const C = {
  b: (t: ReactNode) => <span className="text-[color:var(--brand2)]">{t}</span>,
  g: (t: ReactNode) => <span className="text-[color:var(--pos)]">{t}</span>,
  r: (t: ReactNode) => <span className="text-[color:var(--harm)]">{t}</span>,
  a: (t: ReactNode) => <span className="text-[color:var(--notice)]">{t}</span>,
  m: (t: ReactNode) => <span className="text-muted-foreground">{t}</span>,
};

const HELP = [
  ["simulate", "run the pipeline (--live for Gemini)"],
  ["set K V", "tune a policy limit, e.g. set max_traffic_share 0.25"],
  ["config", "current limits + seed"],
  ["seed N", "set the simulation seed"],
  ["dataset", "the payment world: slices, traffic, order sizes"],
  ["policy", "the boundaries the agent runs inside"],
  ["ledger", "every test and how it ended"],
  ["memory", "what the agent has learned"],
  ["clear", "clear the screen"],
];

export function Terminal({ onRun }: { onRun: (live: boolean, seed: number) => void }) {
  const [lines, setLines] = useState<Line[]>([]);
  const [val, setVal] = useState("");
  const [hist, setHist] = useState<string[]>([]);
  const [hi, setHi] = useState(-1);
  const [seed, setSeed] = useState(42);
  const idRef = useRef(0);
  const bodyRef = useRef<HTMLDivElement>(null);
  const inRef = useRef<HTMLInputElement>(null);

  const push = (node: ReactNode) => setLines((l) => [...l, { id: idRef.current++, node }]);
  useEffect(() => { bodyRef.current?.scrollTo({ top: 1e9 }); }, [lines]);
  useEffect(() => {
    push(<>{C.m("Thaw shell · type ")}{C.b("help")}{C.m(" to start.")}</>);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run(raw: string) {
    const cmd = raw.trim();
    push(<><span className="text-[color:var(--brand2)]">thaw ❯</span> <span className="text-foreground">{cmd}</span></>);
    if (!cmd) return;
    const [name, ...args] = cmd.split(/\s+/);
    try {
      if (name === "help") HELP.forEach(([c, d]) => push(<>{C.b(c.padEnd(12))}{C.m(d)}</>));
      else if (name === "clear") setLines([]);
      else if (name === "simulate") { const live = args.includes("--live"); push(C.m(`${live ? "live Gemini" : "curated"} run · seed ${seed}…`)); onRun(live, seed); }
      else if (name === "seed") { const n = parseInt(args[0], 10); if (Number.isNaN(n)) push(C.r("usage: seed <number>")); else { setSeed(n); push(<>{C.m("seed = ")}{C.b(n)}</>); } }
      else if (name === "config") {
        const d = await getJSON<{ parsed: { limits: Record<string, number>; brake: Record<string, number>; promote: Record<string, number> } }>("/policy");
        const L = d.parsed.limits;
        push(<>{C.m("max_traffic_share ")}{C.b(L.max_traffic_share)}{C.m("   max_loss_per_test_inr ")}{C.b(rupee(L.max_loss_per_test_inr))}</>);
        push(<>{C.m("max_minutes ")}{C.b(L.max_minutes + " (" + Math.round(L.max_minutes / 1440) + "d)")}{C.m("   harm_alpha ")}{C.b(d.parsed.brake.harm_alpha)}{C.m("   alpha ")}{C.b(d.parsed.promote.alpha)}</>);
        push(<>{C.m("seed ")}{C.b(seed)}{C.m("   ·  tune with ")}{C.b("set <key> <value>")}</>);
      } else if (name === "set") {
        const [key, value] = args;
        if (!key || value === undefined) { push(C.r("usage: set <key> <value>   (or: set reset)")); }
        else {
          const r = await fetch(API + "/policy/set", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ key, value }) }).then((x) => x.json());
          if (r.ok) push(<>{C.g("✓ ")}{C.m("policy · ")}{C.b(r.message)}{C.m("  — re-run ")}{C.b("simulate")}{C.m(" to see the effect")}</>);
          else { push(C.r(r.message)); if (r.tunable) push(<>{C.m("tunable: ")}{C.a(r.tunable.join(", "))}</>); }
        }
      }
      else if (name === "dataset") {
        const d = await getJSON<{ total_per_day: number; baseline_completion: number; watched_slices: { slice: string; arrival_per_day: number; avg_order_inr: number }[] }>("/dataset");
        push(<>{C.m("~100k historical checkouts · ")}{C.b(d.total_per_day + "/day")}{C.m(" · baseline completion ")}{C.g((d.baseline_completion * 100).toFixed(1) + "%")}</>);
        push(C.m("watched slices (in the ₹1k–3k window):"));
        d.watched_slices.forEach((s) => push(<>  {C.b(s.slice.padEnd(30))}{C.m(s.arrival_per_day + "/day · avg " + rupee(s.avg_order_inr))}</>));
      } else if (name === "policy") {
        const d = await getJSON<{ parsed: { limits: Record<string, number>; never: string[]; allowed_tests: string[] } }>("/policy");
        const L = d.parsed.limits;
        push(<>{C.m("traffic ≤ ")}{C.b((L.max_traffic_share * 100) + "%")}{C.m(" · loss/test ≤ ")}{C.b(rupee(L.max_loss_per_test_inr))}{C.m(" · horizon ")}{C.b(Math.round(L.max_minutes / 1440) + "d")}</>);
        push(<>{C.m("allowed: ")}{C.g(d.parsed.allowed_tests.join(", "))}</>);
        push(<>{C.m("never: ")}{C.r(d.parsed.never.join(", "))}</>);
      } else if (name === "ledger") {
        const rows = await getJSON<{ headline: string; status: string }[]>("/ledger");
        if (!rows.length) push(C.m("empty — run `simulate` first."));
        rows.slice(-12).forEach((t) => {
          const col = t.status.includes("WINNER") ? C.g : t.status.includes("HARMFUL") || t.status === "BLOCKED" ? C.r : t.status.includes("SMALL") || t.status.includes("DIFFERENCE") ? C.a : C.m;
          push(<>{col(t.status.padEnd(20))}{C.m(t.headline)}</>);
        });
      } else if (name === "memory") {
        const d = await getJSON<{ learnings: { claim: string }[] }>("/memory");
        if (!d.learnings.length) push(C.m("nothing learned yet — run `simulate`."));
        d.learnings.forEach((l) => push(<>{C.b("✦ ")}{C.m(l.claim)}</>));
      } else push(C.r(`unknown command: ${name} (try 'help')`));
    } catch {
      push(C.r(`could not reach the backend at ${API} — is it running on :8100?`));
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-[#070b1c]/80">
      <div className="flex items-center gap-2 border-b border-border px-3.5 py-2">
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" /><span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" /><span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        <span className="ml-2 text-[11px] text-muted-foreground mono">thaw — shell</span>
      </div>
      <div ref={bodyRef} className="mono flex-1 space-y-0.5 overflow-auto px-4 py-3 text-[12.5px] leading-relaxed" onClick={() => inRef.current?.focus()}>
        {lines.map((l) => <div key={l.id} className="whitespace-pre-wrap">{l.node}</div>)}
        <div className="flex items-center gap-2">
          <span className="text-[color:var(--brand2)]">thaw ❯</span>
          <input ref={inRef} value={val} spellCheck={false} autoFocus
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") { run(val); if (val.trim()) setHist((h) => [...h, val]); setVal(""); setHi(-1); }
              else if (e.key === "ArrowUp") { e.preventDefault(); const ni = hi < 0 ? hist.length - 1 : Math.max(0, hi - 1); if (hist[ni] != null) { setHi(ni); setVal(hist[ni]); } }
              else if (e.key === "ArrowDown") { e.preventDefault(); const ni = hi + 1; if (ni >= hist.length) { setHi(-1); setVal(""); } else { setHi(ni); setVal(hist[ni]); } }
            }}
            className="flex-1 bg-transparent text-foreground outline-none caret-[color:var(--brand2)]" />
        </div>
      </div>
    </div>
  );
}
