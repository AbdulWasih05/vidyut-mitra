"use client";

import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CircleDollarSign,
  Home,
  Leaf,
  Menu,
  MessageSquareText,
  ShieldCheck,
  Star,
  Sun,
  UserRound,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  ActivityRow,
  Metrics,
  TrendBucket,
  getActivity,
  getMetrics,
  getTrend,
} from "../lib/api";

type MetricCardProps = {
  title: string;
  value: string;
  note: string;
  icon: React.ReactNode;
};

function MetricCard({ title, value, note, icon }: MetricCardProps) {
  return (
    <div className="rounded-card border border-borderSoft bg-card p-5">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm text-zinc-500">{title}</p>
        <span className="text-zinc-700">{icon}</span>
      </div>
      <p className="text-2xl font-semibold tracking-tight text-blackDeep">{value}</p>
      <p className="mt-2 text-xs text-zinc-500">{note}</p>
    </div>
  );
}

const rupees = (n: number) =>
  `Rs. ${Math.round(n).toLocaleString("en-IN")}`;

const DUMMY_FEEDBACK = [
  {
    id: "fb-001",
    name: "Nikhil R.",
    persona: "Mangaluru · 3 kW sanctioned",
    rating: 5,
    quote:
      "I had no idea I was paying for 1 kW more than I needed. The Fixed Charge Trap flag saved me Rs. 145 every month.",
    time: "2 hours ago",
  },
  {
    id: "fb-002",
    name: "Priya S.",
    persona: "Udupi · Gruha Jyothi enrolled",
    rating: 5,
    quote:
      "First time anyone told me I'm at 96% of my GJ entitlement. The Kannada voice note explained it to my mother.",
    time: "5 hours ago",
  },
  {
    id: "fb-003",
    name: "Sunita K.",
    persona: "Puttur · Non-GJ household",
    rating: 4,
    quote:
      "The solar payback math was clear. 45 months sounded long until I saw the 25-year savings number.",
    time: "Yesterday",
  },
  {
    id: "fb-004",
    name: "Rohan M.",
    persona: "Mangaluru · 2 kW sanctioned",
    rating: 5,
    quote:
      "Sent a bill photo on WhatsApp, got the analysis in 12 seconds. No app to install. This is how it should work.",
    time: "Yesterday",
  },
  {
    id: "fb-005",
    name: "Anjali D.",
    persona: "Karkala · Non-GJ household",
    rating: 4,
    quote:
      "Wish the infographic was a bit more detailed, but the savings breakdown is exactly what I needed.",
    time: "2 days ago",
  },
  {
    id: "fb-006",
    name: "Vikas B.",
    persona: "Mangaluru · Solar adopter",
    rating: 5,
    quote:
      "The PM Surya Ghar subsidy walkthrough made the application 10x less intimidating. Highly recommend.",
    time: "3 days ago",
  },
];

const statusClass = (status: string) => {
  if (status === "Cliff Crossed" || status === "FCT Flagged") {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }
  if (status === "Approaching") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  if (status === "Subsidised") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  return "border-zinc-200 bg-zinc-50 text-zinc-700";
};

export default function DashboardShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [activities, setActivities] = useState<ActivityRow[]>([]);
  const [trend, setTrend] = useState<TrendBucket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>("never");

  async function refresh() {
    try {
      setError(null);
      const [m, a, t] = await Promise.all([
        getMetrics(),
        getActivity(10),
        getTrend(),
      ]);
      setMetrics(m);
      setActivities(a.rows);
      setTrend(t.buckets);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 60_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const trendMaxRupees = useMemo(() => {
    const values = trend.flatMap((b) => [b.avg_bill, b.avg_solar_bill]);
    return values.length ? Math.max(...values, 1) : 1;
  }, [trend]);

  return (
    <div id="top" className="min-h-screen bg-cream text-blackDeep scroll-smooth">
      {mobileOpen ? (
        <button
          aria-label="Close menu overlay"
          className="fixed inset-0 z-30 bg-black/35 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <aside
        className={[
          "fixed inset-y-0 left-0 z-40 w-72 bg-blackDeep text-white transition-transform duration-200",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          "md:translate-x-0",
        ].join(" ")}
      >
        <div className="flex h-full flex-col px-5 py-6">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-zinc-400">Official</p>
              <p className="text-xl font-semibold">VidyutMitra</p>
            </div>
            <button
              className="rounded-md border border-zinc-700 p-2 md:hidden"
              onClick={() => setMobileOpen(false)}
              aria-label="Close sidebar"
            >
              <X size={16} />
            </button>
          </div>

          <nav className="space-y-2 text-sm">
            <Link
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-zinc-300 hover:bg-zinc-900"
              href="/"
              onClick={() => setMobileOpen(false)}
            >
              <ArrowLeft size={16} /> Back to Landing
            </Link>
            <a
              className="flex items-center gap-3 rounded-lg border border-zinc-700/80 bg-zinc-900 px-3 py-2"
              href="#top"
              onClick={() => setMobileOpen(false)}
            >
              <Home size={16} /> Dashboard
            </a>
            <a
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-zinc-300 hover:bg-zinc-900"
              href="#analytics"
              onClick={() => setMobileOpen(false)}
            >
              <BarChart3 size={16} /> Analytics
            </a>
            <a
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-zinc-300 hover:bg-zinc-900"
              href="#activity"
              onClick={() => setMobileOpen(false)}
            >
              <MessageSquareText size={16} /> Activity
            </a>
            <a
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-zinc-300 hover:bg-zinc-900"
              href="#feedback"
              onClick={() => setMobileOpen(false)}
            >
              <Star size={16} /> Feedback
            </a>
            <a
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-zinc-300 hover:bg-zinc-900"
              href="#dpdpa"
              onClick={() => setMobileOpen(false)}
            >
              <ShieldCheck size={16} /> DPDPA
            </a>
          </nav>

          <div className="mt-auto rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-sm">
            <p className="font-medium">System Status</p>
            <p className="mt-1 text-zinc-400">
              {error ? "Backend unreachable." : "All webhook services operational."}
            </p>
            <p className="mt-3 text-xs text-zinc-500">Updated {lastUpdated}</p>
          </div>
        </div>
      </aside>

      <main className="md:ml-72">
        <header className="sticky top-0 z-20 border-b border-zinc-200 bg-cream/90 px-4 py-4 backdrop-blur md:px-8">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                className="rounded-lg border border-zinc-300 bg-white p-2 md:hidden"
                onClick={() => setMobileOpen(true)}
                aria-label="Open sidebar"
              >
                <Menu size={18} />
              </button>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">VidyutMitra</p>
                <h1 className="text-xl font-semibold">MESCOM Impact Dashboard</h1>
                <p className="mt-0.5 text-xs text-zinc-500">
                  Aggregate view · No personal data · Refreshes every 60s
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="hidden items-center gap-2 rounded-xl border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 sm:inline-flex"
              >
                <ArrowLeft size={16} /> Landing
              </Link>
              <div className="flex items-center gap-3 rounded-xl border border-zinc-300 bg-white px-3 py-2 text-sm">
                <UserRound size={16} />
                <span>Admin</span>
              </div>
            </div>
          </div>
        </header>

        <section className="space-y-6 px-4 py-6 md:px-8">
          {error ? (
            <div className="rounded-card border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              <p className="font-medium">Cannot reach admin API.</p>
              <p className="mt-1">{error}</p>
              <p className="mt-2 text-xs text-rose-600">
                Make sure Flask is running on port 5001 and NEXT_PUBLIC_ADMIN_PASSWORD
                matches the server&apos;s ADMIN_PASSWORD.
              </p>
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <MetricCard
              title="Avg Bill (solar-eligible)"
              value={metrics ? rupees(metrics.avg_non_gj_bill_rupees) : "—"}
              note="Non-GJ households — the cohort where solar matters"
              icon={<CircleDollarSign size={18} />}
            />
            <MetricCard
              title="Avg Bill After 3 kW Solar"
              value={metrics ? rupees(metrics.avg_solar_bill_rupees) : "—"}
              note="Same cohort, post PM Surya Ghar install"
              icon={<Sun size={18} />}
            />
            <MetricCard
              title="Avg Monthly Savings"
              value={metrics ? rupees(metrics.avg_monthly_solar_savings_rupees) : "—"}
              note="Per household · 3 kW system · KERC 2025 tariffs"
              icon={<BarChart3 size={18} />}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="Consented Users"
              value={metrics ? metrics.consented_users.toString() : "—"}
              note={`${metrics?.total_bills ?? 0} bills analysed`}
              icon={<Users size={18} />}
            />
            <MetricCard
              title="Fixed Charge Trap flags"
              value={metrics ? metrics.fct_flags_fired.toString() : "—"}
              note="Households over-provisioned"
              icon={<AlertTriangle size={18} />}
            />
            <MetricCard
              title="GJ Subsidy Made Visible"
              value={metrics ? rupees(metrics.gj_subsidy_visible_rupees) : "—"}
              note={`${metrics?.gj_bills ?? 0} Gruha Jyothi bills`}
              icon={<ShieldCheck size={18} />}
            />
            <MetricCard
              title="Annual CO2 Footprint"
              value={
                metrics ? `${metrics.annual_co2_footprint_tonnes.toFixed(1)} t` : "—"
              }
              note="Across consented households"
              icon={<Leaf size={18} />}
            />
          </div>

          <div
            id="analytics"
            className="scroll-mt-24 rounded-card border border-borderSoft bg-card p-5"
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Avg Bill vs Solar-Replaced Bill</h2>
                <p className="text-sm text-zinc-500">Last 8 days</p>
              </div>
              <span className="text-xs text-zinc-500">
                <span className="mr-3 inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-4 bg-black" /> Grid bill
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-4 bg-zinc-400" /> With solar
                </span>
              </span>
            </div>
            <div className="h-80 rounded-xl border border-dashed border-zinc-300 bg-zinc-50 p-4">
              {trend.length === 0 ? (
                <div className="flex h-full items-center justify-center text-sm text-zinc-400">
                  No bills in the last 8 days. Seed demo data with{" "}
                  <code className="mx-1 rounded bg-zinc-200 px-1">python scripts/seed_demo_data.py</code>
                </div>
              ) : (
                <div className="flex h-full flex-col justify-between">
                  <div className="grid h-full grid-cols-8 gap-2">
                    {trend.map((b) => (
                      <div key={`grid-${b.date}`} className="flex flex-col justify-end">
                        <div
                          className="w-full rounded-t bg-black"
                          style={{ height: `${(b.avg_bill / trendMaxRupees) * 100}%` }}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 grid h-full grid-cols-8 gap-2">
                    {trend.map((b) => (
                      <div key={`solar-${b.date}`} className="flex flex-col justify-end">
                        <div
                          className="w-full rounded-t bg-zinc-400"
                          style={{ height: `${(b.avg_solar_bill / trendMaxRupees) * 100}%` }}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="mt-2 grid grid-cols-8 gap-2 text-[10px] text-zinc-400">
                    {trend.map((b) => (
                      <span key={`lbl-${b.date}`} className="text-center">
                        {b.date.slice(5)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div
            id="activity"
            className="scroll-mt-24 rounded-card border border-borderSoft bg-card p-5"
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Recent Activity</h2>
                <p className="text-sm text-zinc-500">
                  Anonymised log. Phone numbers and names are never surfaced here.
                </p>
              </div>
              <span className="text-sm text-zinc-500">Last {activities.length}</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 text-zinc-500">
                    <th className="py-3 font-medium">Log ID</th>
                    <th className="py-3 font-medium">Units</th>
                    <th className="py-3 font-medium">Net Bill</th>
                    <th className="py-3 font-medium">Source</th>
                    <th className="py-3 font-medium">Status</th>
                    <th className="py-3 font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {activities.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-zinc-400">
                        No activity yet.
                      </td>
                    </tr>
                  ) : (
                    activities.map((row) => (
                      <tr key={row.log_id} className="border-b border-zinc-100 last:border-0">
                        <td className="py-3 font-medium">{row.log_id}</td>
                        <td className="py-3">{row.units_consumed}</td>
                        <td className="py-3">{rupees(row.net_bill_rupees)}</td>
                        <td className="py-3">{row.source}</td>
                        <td className="py-3">
                          <span
                            className={[
                              "inline-flex rounded-full border px-2 py-1 text-xs",
                              statusClass(row.status),
                            ].join(" ")}
                          >
                            {row.status}
                          </span>
                        </td>
                        <td className="py-3 text-zinc-500">{row.time}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div
            id="feedback"
            className="scroll-mt-24 rounded-card border border-borderSoft bg-card p-5"
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">User Feedback</h2>
                <p className="text-sm text-zinc-500">
                  Anonymised testimonials from consented users · sample data
                </p>
              </div>
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-sm text-amber-700">
                <Star size={14} className="fill-amber-500 text-amber-500" />
                4.6 / 5 avg
              </span>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {DUMMY_FEEDBACK.map((fb) => (
                <div
                  key={fb.id}
                  className="flex h-full flex-col rounded-lg border border-zinc-200 bg-white p-4"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-sm font-medium text-blackDeep">{fb.name}</p>
                    <div className="flex items-center gap-0.5">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star
                          key={i}
                          size={14}
                          className={
                            i < fb.rating
                              ? "fill-amber-500 text-amber-500"
                              : "text-zinc-300"
                          }
                        />
                      ))}
                    </div>
                  </div>
                  <p className="text-xs uppercase tracking-wider text-zinc-500">
                    {fb.persona}
                  </p>
                  <p className="mt-3 flex-1 text-sm leading-relaxed text-zinc-700">
                    &ldquo;{fb.quote}&rdquo;
                  </p>
                  <p className="mt-3 text-xs text-zinc-400">{fb.time}</p>
                </div>
              ))}
            </div>
          </div>

          <div
            id="dpdpa"
            className="scroll-mt-24 rounded-card border border-borderSoft bg-card p-5"
          >
            <div className="mb-4">
              <h2 className="text-lg font-semibold">DPDPA Compliance</h2>
              <p className="text-sm text-zinc-500">
                Digital Personal Data Protection Act, 2023 — by design, not by checkbox.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm">
                <p className="font-semibold text-emerald-800">Consent before processing</p>
                <p className="mt-1 text-emerald-700">
                  Every user sees the privacy notice in Kannada + English and must
                  reply <code className="rounded bg-white/60 px-1">START</code>.
                  Unconsented messages are never forwarded to Gemini.
                </p>
                <p className="mt-2 text-xs text-emerald-700">
                  {metrics ? `${metrics.consented_users} of ${metrics.total_users}` : "—"}{" "}
                  users consented
                </p>
              </div>

              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm">
                <p className="font-semibold text-emerald-800">Bill images never stored</p>
                <p className="mt-1 text-emerald-700">
                  The <code className="rounded bg-white/60 px-1">bills</code> schema
                  has no <code className="rounded bg-white/60 px-1">bill_image</code>,{" "}
                  <code className="rounded bg-white/60 px-1">bill_url</code>, or any
                  raw-image column. <code className="rounded bg-white/60 px-1">write_bill</code>{" "}
                  raises on any such field.
                </p>
              </div>

              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm">
                <p className="font-semibold text-emerald-800">STOP is a hard delete</p>
                <p className="mt-1 text-emerald-700">
                  One-word opt-out. User row + cascaded bills gone immediately. No soft
                  delete, no <code className="rounded bg-white/60 px-1">deleted_at</code>{" "}
                  column, no recovery.
                </p>
              </div>

              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm">
                <p className="font-semibold text-emerald-800">Aggregate-only dashboard</p>
                <p className="mt-1 text-emerald-700">
                  Every query on this page is <code className="rounded bg-white/60 px-1">COUNT</code>/
                  <code className="rounded bg-white/60 px-1">AVG</code>/
                  <code className="rounded bg-white/60 px-1">SUM</code> or anonymised.
                  No route surfaces phone number, consumer name, or RR number.
                </p>
              </div>
            </div>

            <p className="mt-4 text-xs text-zinc-500">
              Sources: CLAUDE.md §3 Rule 2 · tech spec §9 (DPDPA Compliance Design) ·
              PRD §3.1 M8 (Consent flow).
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
