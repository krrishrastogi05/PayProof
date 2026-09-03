export const API = process.env.NEXT_PUBLIC_THAW_API || "http://127.0.0.1:8100";

export type ThawEvent = {
  seq: number; sim_ts: number; kind: string;
  [k: string]: unknown;
};

export const getJSON = <T,>(p: string): Promise<T> => fetch(API + p).then((r) => r.json());

export function openStream(live: boolean, onEvent: (e: ThawEvent) => void, onDone: () => void): EventSource {
  const es = new EventSource(`${API}/stream${live ? "?live=1" : ""}`);
  es.onmessage = (m) => { try { onEvent(JSON.parse(m.data)); } catch { /* ignore */ } };
  es.addEventListener("done", () => { es.close(); onDone(); });
  es.onerror = () => { es.close(); onDone(); };
  return es;
}

export const rupee = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");

// which pipeline stage a card belongs to
export const STAGE_OF: Record<string, string> = {
  WATCHING: "watcher", THINKING: "reasoner", PROPOSED: "reasoner",
  BLOCKED: "rules", TOO_SMALL: "feasibility", CAP_SET: "feasibility",
  RUNNING: "runner", BRAKE_PULLED: "scoreboard", KEPT: "scoreboard",
  NO_DIFFERENCE: "scoreboard", STOPPED_BAD_SPLIT: "scoreboard",
  REVERTED: "memory", LEARNED: "memory",
};

export const STAGE_ORDER = ["watcher", "reasoner", "rules", "feasibility", "runner", "scoreboard", "memory"];
