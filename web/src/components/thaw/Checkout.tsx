"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, CreditCard, Landmark, ShieldCheck, Clock, RefreshCw } from "lucide-react";
import type { ThawEvent } from "@/lib/thaw";

/* ---------- payment method logos (real brand marks via CDN, crafted fallbacks) ---------- */
function CdnLogo({ slug, color, alt }: { slug: string; color?: string; alt: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={`https://cdn.simpleicons.org/${slug}${color ? "/" + color : ""}`} alt={alt}
      className="h-4 w-4" width={16} height={16} />
  );
}
const METHODS: Record<string, { label: string; logo: React.ReactNode; tint: string }> = {
  upi: { label: "UPI", tint: "#0b7d3c", logo: <span className="mono text-[9px] font-bold tracking-tight"><span style={{ color: "#f36f21" }}>U</span><span style={{ color: "#0b7d3c" }}>P</span><span style={{ color: "#0b7d3c" }}>I</span></span> },
  gpay: { label: "Google Pay", tint: "#4285F4", logo: <CdnLogo slug="googlepay" alt="Google Pay" /> },
  phonepe: { label: "PhonePe", tint: "#5F259F", logo: <CdnLogo slug="phonepe" color="5F259F" alt="PhonePe" /> },
  paytm: { label: "Paytm", tint: "#00BAF2", logo: <CdnLogo slug="paytm" color="00BAF2" alt="Paytm" /> },
  card: { label: "Cards", tint: "#1a1f36", logo: <CreditCard className="h-4 w-4 text-[#1a1f36]" /> },
  netbanking: { label: "Netbanking", tint: "#334155", logo: <Landmark className="h-4 w-4 text-slate-600" /> },
};
const UPI_FIRST = ["upi", "gpay", "phonepe", "card", "netbanking"];
const CARDS_FIRST = ["card", "upi", "gpay", "phonepe", "netbanking"];

/* ---------- one Razorpay-style checkout ---------- */
function Checkout({ order, amount, rate, state, tag, tagTone }: {
  order: string[]; amount: number; rate?: number; state: "idle" | "success" | "reverted"; tag: string; tagTone: string;
}) {
  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-black/5 bg-white text-[#1a1f36] shadow-xl">
      {/* header */}
      <div className="flex items-center justify-between bg-[#0d1836] px-4 py-3 text-white">
        <div>
          <div className="text-[13px] font-semibold">Acme Electronics</div>
          <div className="flex items-center gap-1 text-[10px] text-white/70"><ShieldCheck className="h-3 w-3" /> Razorpay Trusted Business</div>
        </div>
        <span className="rounded-md px-2 py-0.5 text-[10px] font-semibold" style={{ background: tagTone + "22", color: tagTone }}>{tag}</span>
      </div>
      {/* order */}
      <div className="flex items-center justify-between border-b border-black/5 px-4 py-2.5">
        <span className="text-[12px] text-slate-500">Order total</span>
        <span className="mono text-[15px] font-semibold">₹{amount.toLocaleString("en-IN")}</span>
      </div>
      {/* methods */}
      <div className="px-3 py-2.5">
        <div className="mb-1.5 px-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Payment methods</div>
        <div className="space-y-1">
          {order.slice(0, 4).map((m, i) => {
            const meta = METHODS[m];
            return (
              <div key={m} className={`flex items-center gap-2.5 rounded-lg border px-2.5 py-2 ${i === 0 ? "border-[#3395ff]/40 bg-[#3395ff]/5" : "border-black/5"}`}>
                <span className="grid h-6 w-6 place-items-center rounded-md bg-white ring-1 ring-black/5">{meta.logo}</span>
                <span className="text-[12.5px] font-medium">{meta.label}</span>
                {i === 0 && <span className="ml-auto text-[10px] font-semibold text-[#3395ff]">shown first</span>}
              </div>
            );
          })}
        </div>
      </div>
      {rate != null && (
        <div className="px-4 pb-2">
          <div className="flex items-center justify-between text-[11px] text-slate-500"><span>completion</span><span className="mono font-semibold text-[#1a1f36]">{rate.toFixed(1)}%</span></div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-[#3395ff] transition-all duration-500" style={{ width: `${Math.min(100, rate)}%` }} /></div>
        </div>
      )}
      <div className="px-4 pb-3 pt-1">
        <div className="rounded-lg bg-[#3395ff] py-2 text-center text-[13px] font-semibold text-white">Pay ₹{amount.toLocaleString("en-IN")}</div>
        <div className="mt-2 text-center text-[9px] text-slate-400">Secured by <span className="font-semibold text-[#3395ff]">Razorpay</span></div>
      </div>

      {/* success overlay */}
      <AnimatePresence>
        {state === "success" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#1aa260] text-white">
            <div className="text-[13px] font-medium opacity-90">Payment Successful</div>
            <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 260, damping: 14 }}
              className="grid h-16 w-16 place-items-center rounded-full bg-white/20 ring-4 ring-white/30">
              <Check className="h-8 w-8" strokeWidth={3} />
            </motion.div>
            <div className="mono text-[20px] font-bold">₹{amount.toLocaleString("en-IN")}</div>
            <div className="text-[10px] opacity-80">Secured by Razorpay</div>
          </motion.div>
        )}
        {state === "reverted" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-[#c0341d]/95 text-white">
            <div className="text-[15px] font-semibold">Reverted</div>
            <div className="max-w-[70%] text-center text-[11px] opacity-85">this order hurt completion — the brake rolled it back</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function outcomeState(kind?: string): "idle" | "success" | "reverted" {
  if (kind === "KEPT") return "success";
  if (kind === "BRAKE_PULLED" || kind === "REVERTED" || kind === "STOPPED_BAD_SPLIT") return "reverted";
  return "idle";
}

/* ---------- the A/B pair, driven by the live test ---------- */
export function CheckoutAB({ event, rc, rt, amount = 2000 }: { event: ThawEvent | null; rc?: number; rt?: number; amount?: number }) {
  const treatState = outcomeState(event?.kind);
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div>
        <div className="mb-2 text-[12px] text-muted-foreground">Control — <span className="text-foreground">UPI shown first</span> (the frozen setting)</div>
        <Checkout order={UPI_FIRST} amount={amount} rate={rc} state="idle" tag="CONTROL" tagTone="#64748b" />
      </div>
      <div>
        <div className="mb-2 text-[12px] text-muted-foreground">Treatment — <span className="text-foreground">Cards shown first</span> (the test)</div>
        <Checkout order={CARDS_FIRST} amount={amount} rate={rt} state={treatState} tag="TREATMENT" tagTone="#3395ff" />
      </div>
    </div>
  );
}

/* ---------- a retry-timing card: same shell, a failed-charge recovery schedule ---------- */
function RetryCard({ schedule, note, rate, state, tag, tagTone, amount }: {
  schedule: string[]; note: string; rate?: number; state: "idle" | "success" | "reverted"; tag: string; tagTone: string; amount: number;
}) {
  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-black/5 bg-white text-[#1a1f36] shadow-xl">
      <div className="flex items-center justify-between bg-[#0d1836] px-4 py-3 text-white">
        <div>
          <div className="text-[13px] font-semibold">Acme Electronics</div>
          <div className="flex items-center gap-1 text-[10px] text-white/70"><ShieldCheck className="h-3 w-3" /> Razorpay Trusted Business</div>
        </div>
        <span className="rounded-md px-2 py-0.5 text-[10px] font-semibold" style={{ background: tagTone + "22", color: tagTone }}>{tag}</span>
      </div>
      <div className="flex items-center justify-between border-b border-black/5 px-4 py-2.5">
        <span className="flex items-center gap-1.5 text-[12px] text-slate-500"><RefreshCw className="h-3.5 w-3.5 text-[#c0341d]" /> Charge failed · retrying</span>
        <span className="mono text-[15px] font-semibold">₹{amount.toLocaleString("en-IN")}</span>
      </div>
      <div className="px-3 py-2.5">
        <div className="mb-1.5 px-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Retry schedule</div>
        <div className="flex items-center gap-1.5">
          {schedule.map((s, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <span className={`inline-flex items-center gap-1 rounded-lg border px-2 py-1.5 text-[11.5px] font-medium ${i === 0 ? "border-[#3395ff]/40 bg-[#3395ff]/5" : "border-black/5"}`}>
                <Clock className="h-3 w-3 text-slate-400" />{s}
              </span>
              {i < schedule.length - 1 && <span className="text-slate-300">→</span>}
            </div>
          ))}
        </div>
        <div className="mt-2 px-1 text-[10.5px] text-slate-500">{note}</div>
      </div>
      {rate != null && (
        <div className="px-4 pb-2">
          <div className="flex items-center justify-between text-[11px] text-slate-500"><span>recovery rate</span><span className="mono font-semibold text-[#1a1f36]">{rate.toFixed(1)}%</span></div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-[#3395ff] transition-all duration-500" style={{ width: `${Math.min(100, rate)}%` }} /></div>
        </div>
      )}
      <div className="px-4 pb-3 pt-1">
        <div className="rounded-lg bg-[#3395ff] py-2 text-center text-[13px] font-semibold text-white">Retry payment</div>
        <div className="mt-2 text-center text-[9px] text-slate-400">Secured by <span className="font-semibold text-[#3395ff]">Razorpay</span></div>
      </div>
      <AnimatePresence>
        {state === "success" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#1aa260] text-white">
            <div className="text-[13px] font-medium opacity-90">Payment Recovered</div>
            <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 260, damping: 14 }}
              className="grid h-16 w-16 place-items-center rounded-full bg-white/20 ring-4 ring-white/30">
              <Check className="h-8 w-8" strokeWidth={3} />
            </motion.div>
            <div className="mono text-[20px] font-bold">₹{amount.toLocaleString("en-IN")}</div>
            <div className="text-[10px] opacity-80">recovered on a later retry</div>
          </motion.div>
        )}
        {state === "reverted" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-[#c0341d]/95 text-white">
            <div className="text-[15px] font-semibold">Reverted</div>
            <div className="max-w-[70%] text-center text-[11px] opacity-85">this schedule recovered fewer charges — the brake rolled it back</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function RetryAB({ event, rc, rt, amount = 2000 }: { event: ThawEvent | null; rc?: number; rt?: number; amount?: number }) {
  const treatState = outcomeState(event?.kind);
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div>
        <div className="mb-2 text-[12px] text-muted-foreground">Control — <span className="text-foreground">retry at 30 min</span> (the frozen setting)</div>
        <RetryCard schedule={["30 min", "2 h", "6 h"]} note="first retry fires while the bank is still cooling off" rate={rc} state="idle" tag="CONTROL" tagTone="#64748b" amount={amount} />
      </div>
      <div>
        <div className="mb-2 text-[12px] text-muted-foreground">Treatment — <span className="text-foreground">wait 6 h first</span> (the test)</div>
        <RetryCard schedule={["6 h", "24 h"]} note="give the issuing bank time to recover before retrying" rate={rt} state={treatState} tag="TREATMENT" tagTone="#3395ff" amount={amount} />
      </div>
    </div>
  );
}
