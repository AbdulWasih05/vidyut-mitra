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
  isApiConfigured,
} from "../lib/api";
import { MOCK_ACTIVITY, MOCK_METRICS, makeMockTrend } from "../lib/mock-data";

type MetricCardProps = {
  title: string;
  value: string;
  note: string;
  icon: React.ReactNode;
  accent?: "green" | "terracotta";
};

function MetricCard({ title, value, note, icon, accent = "green" }: MetricCardProps) {
  return (
    <div className="rounded-card border border-ink/10 bg-paper p-5 shadow-card">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm text-ink-soft">{title}</p>
        <span
          className={[
            "flex h-8 w-8 items-center justify-center rounded-full",
            accent === "terracotta"
              ? "bg-terracotta/10 text-terracotta"
              : "bg-green/10 text-green-deep",
          ].join(" ")}
        >
          {icon}
        </span>
      </div>
      <p className="font-serif text-3xl font-semibold tracking-tight text-ink">{value}</p>
      <p className="mt-2 text-xs text-ink-faint">{note}</p>
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
    return "border-terracotta/30 bg-terracotta/10 text-bronze";
  }
  if (status === "Approaching") {
    return "border-gold/40 bg-gold/15 text-amber-800";
  }
  if (status === "Subsidised") {
    return "border-green/30 bg-green/10 text-green-deep";
  }
  return "border-ink/10 bg-cream-2 text-ink-soft";
};

export default function DashboardShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [activities, setActivities] = useState<ActivityRow[]>([]);
  const [trend, setTrend] = useState<TrendBucket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>("never");
  const [useMock, setUseMock] = useState(false);
  const [usingMock, setUsingMock] = useState(false);
  const [backendOff, setBackendOff] = useState(false);

  function showMockData() {
    setMetrics(MOCK_METRICS);
    setActivities(MOCK_ACTIVITY);
    setTrend(makeMockTrend());
    setUsingMock(true);
    setLastUpdated(new Date().toLocaleTimeString());
  }

  async function refresh() {
    // No hosted backend and not on localhost: use mock data without
    // firing fetches that would spam the console with network errors.
    if (!isApiConfigured()) {
      setBackendOff(true);
      setError(null);
      showMockData();
      return;
    }
    if (useMock) {
      setError(null);
      showMockData();
      return;
    }
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
      setUsingMock(false);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      showMockData();
    }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 60_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [useMock]);

  const trendMaxRupees = useMemo(() => {
    const values = trend.flatMap((b) => [b.avg_bill, b.avg_solar_bill]);
    return values.length ? Math.max(...values, 1) : 1;
  }, [trend]);

  return (
    <div id="top" className="min-h-screen bg-cream text-ink scroll-smooth">
      {mobileOpen ? (
        <button
          aria-label="Close menu overlay"
          className="fixed inset-0 z-30 bg-black/35 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <aside
        className={[
          "vm-sidebar-bg fixed inset-y-0 left-0 z-40 w-72 overflow-hidden text-[#eef6f0] transition-transform duration-200",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          "md:translate-x-0",
        ].join(" ")}
      >
        <div
          aria-hidden
          className="vm-jaali pointer-events-none absolute inset-0 opacity-[0.07]"
        />
        <div className="relative z-10 flex h-full flex-col px-5 py-6">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <p className="text-[11px] uppercase tracking-[0.28em] text-marigold/80">
                Official
              </p>
              <p className="font-serif text-2xl font-semibold tracking-tight text-white">
                Vidyut<span className="text-marigold">Mitra</span>
              </p>
            </div>
            <button
              className="rounded-full border border-white/20 p-2 text-[#cfe0d6] hover:bg-white/10 md:hidden"
              onClick={() => setMobileOpen(false)}
              aria-label="Close sidebar"
            >
              <X size={16} />
            </button>
          </div>

          <nav className="space-y-2 text-sm">
            <Link
              className="flex items-center gap-3 rounded-full px-4 py-2 text-marigold/90 transition hover:bg-white/10 hover:text-marigold"
              href="/"
              onClick={() => setMobileOpen(false)}
            >
              <ArrowLeft size={16} /> Back to Landing
            </Link>
            <a
              className="flex items-center gap-3 rounded-full border border-marigold/40 bg-white/10 px-4 py-2 font-medium text-white"
              href="#top"
              onClick={() => setMobileOpen(false)}
            >
              <Home size={16} /> Dashboard
              <span className="ml-auto h-1.5 w-1.5 rounded-full bg-marigold" />
            </a>
            <a
              className="flex items-center gap-3 rounded-full px-4 py-2 text-[#cfe0d6] transition hover:bg-white/10 hover:text-white"
              href="#analytics"
              onClick={() => setMobileOpen(false)}
            >
              <BarChart3 size={16} /> Analytics
            </a>
            <a
              className="flex items-center gap-3 rounded-full px-4 py-2 text-[#cfe0d6] transition hover:bg-white/10 hover:text-white"
              href="#activity"
              onClick={() => setMobileOpen(false)}
            >
              <MessageSquareText size={16} /> Activity
            </a>
            <a
              className="flex items-center gap-3 rounded-full px-4 py-2 text-[#cfe0d6] transition hover:bg-white/10 hover:text-white"
              href="#feedback"
              onClick={() => setMobileOpen(false)}
            >
              <Star size={16} /> Feedback
            </a>
            <a
              className="flex items-center gap-3 rounded-full px-4 py-2 text-[#cfe0d6] transition hover:bg-white/10 hover:text-white"
              href="#dpdpa"
              onClick={() => setMobileOpen(false)}
            >
              <ShieldCheck size={16} /> DPDPA
            </a>
          </nav>

          <div className="mt-auto rounded-xl border border-white/10 bg-black/25 p-4 text-sm backdrop-blur-sm">
            <p className="flex items-center gap-2 font-serif font-medium text-white">
              <span
                className={[
                  "inline-block h-2 w-2 rounded-full",
                  error || backendOff
                    ? "bg-terracotta shadow-[0_0_0_3px_rgba(217,113,78,0.2)]"
                    : "bg-marigold shadow-[0_0_0_3px_rgba(134,217,180,0.2)]",
                ].join(" ")}
              />
              System Status
            </p>
            <p className="mt-1 text-[#cfe0d6]/80">
              {error || backendOff
                ? "Backend not hosted - showing mock data."
                : usingMock
                  ? "Mock data mode - live fetches paused."
                  : "All webhook services operational."}
            </p>
            {backendOff ? null : (
              <button
                onClick={() => setUseMock((v) => !v)}
                className={[
                  "mt-3 flex w-full items-center justify-between rounded-full border px-3 py-1.5 text-xs transition",
                  useMock
                    ? "border-gold/40 bg-gold/15 text-gold"
                    : "border-white/15 text-[#cfe0d6] hover:bg-white/10",
                ].join(" ")}
              >
                Mock data
                <span className="font-medium">{useMock ? "On" : "Off"}</span>
              </button>
            )}
            <p className="mt-3 text-[11px] text-marigold/70">Updated {lastUpdated}</p>
          </div>
        </div>
      </aside>

      <main className="md:ml-72">
        <header className="sticky top-0 z-20 border-b border-ink/10 bg-paper/85 px-4 py-4 backdrop-blur md:px-8">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                className="rounded-full border border-ink/10 bg-paper-2 p-2 text-ink-soft md:hidden"
                onClick={() => setMobileOpen(true)}
                aria-label="Open sidebar"
              >
                <Menu size={18} />
              </button>
              <div>
                <p className="text-[11px] uppercase tracking-[0.2em] text-green-deep">
                  VidyutMitra
                </p>
                <h1 className="font-serif text-2xl font-semibold tracking-tight text-ink">
                  MESCOM Impact Dashboard
                </h1>
                <p className="mt-0.5 text-xs text-ink-faint">
                  Aggregate view · No personal data · Refreshes every 60s
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {/* <Link
                href="/"
                className="hidden items-center gap-2 rounded-full border border-ink/10 bg-paper-2 px-4 py-2 text-sm text-ink-soft transition hover:border-green/40 hover:text-green-deep sm:inline-flex"
              >
                <ArrowLeft size={16} /> Landing
              </Link> */}
              <div className="hidden items-center gap-2 rounded-full border border-ink/10 bg-paper-2 px-4 py-2 text-sm text-ink-soft sm:flex">
                <UserRound size={16} />
                <span>Admin</span>
              </div>
            </div>
          </div>
        </header>

        <section className="space-y-6 px-4 py-6 md:px-8">
          {/* {error ? (
            <div className="rounded-card border border-terracotta/30 bg-terracotta/10 p-4 text-sm text-bronze">
              <p className="font-medium">
                Cannot reach admin API. Showing mock data below.
              </p>
              <p className="mt-1">{error}</p>
              <p className="mt-2 text-xs text-terracotta">
                Make sure Flask is running on port 5001 and NEXT_PUBLIC_ADMIN_PASSWORD
                matches the server&apos;s ADMIN_PASSWORD.
              </p>
            </div>
          ) : null} */}

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <MetricCard
              title="Avg Bill (solar-eligible)"
              value={metrics ? rupees(metrics.avg_non_gj_bill_rupees) : "-"}
              note="Non-GJ households - the cohort where solar matters"
              icon={<CircleDollarSign size={18} />}
            />
            <MetricCard
              title="Avg Bill After 3 kW Solar"
              value={metrics ? rupees(metrics.avg_solar_bill_rupees) : "-"}
              note="Same cohort, post PM Surya Ghar install"
              icon={<Sun size={18} />}
            />
            <MetricCard
              title="Avg Monthly Savings"
              value={metrics ? rupees(metrics.avg_monthly_solar_savings_rupees) : "-"}
              note="Per household · 3 kW system · KERC 2025 tariffs"
              icon={<BarChart3 size={18} />}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="Consented Users"
              value={metrics ? metrics.consented_users.toString() : "-"}
              note={`${metrics?.total_bills ?? 0} bills analysed`}
              icon={<Users size={18} />}
            />
            <MetricCard
              title="Fixed Charge Trap flags"
              value={metrics ? metrics.fct_flags_fired.toString() : "-"}
              note="Households over-provisioned"
              icon={<AlertTriangle size={18} />}
              accent="terracotta"
            />
            <MetricCard
              title="GJ Subsidy Made Visible"
              value={metrics ? rupees(metrics.gj_subsidy_visible_rupees) : "-"}
              note={`${metrics?.gj_bills ?? 0} Gruha Jyothi bills`}
              icon={<ShieldCheck size={18} />}
            />
            <MetricCard
              title="Annual CO2 Footprint"
              value={
                metrics ? `${metrics.annual_co2_footprint_tonnes.toFixed(1)} t` : "-"
              }
              note="Across consented households"
              icon={<Leaf size={18} />}
            />
          </div>

          <div
            id="analytics"
            className="scroll-mt-24 rounded-card border border-ink/10 bg-paper p-5 shadow-card"
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="font-serif text-xl font-semibold text-ink">
                  Avg Bill vs Solar-Replaced Bill
                </h2>
                <p className="text-sm text-ink-faint">Last 8 days</p>
              </div>
              <span className="text-xs text-ink-soft">
                <span className="mr-3 inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-4 rounded-sm bg-green-deep" /> Grid bill
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-4 rounded-sm bg-marigold" /> With solar
                </span>
              </span>
            </div>
            <div className="h-80 rounded-xl border border-dashed border-ink/10 bg-cream-2/60 p-4">
              {trend.length === 0 ? (
                <div className="flex h-full items-center justify-center text-sm text-ink-faint">
                  No bills in the last 8 days. Seed demo data with{" "}
                  <code className="mx-1 rounded bg-cream-2 px-1 text-green-ink">python scripts/seed_demo_data.py</code>
                </div>
              ) : (
                <div className="flex h-full flex-col justify-between">
                  <div className="grid h-full grid-cols-8 gap-2">
                    {trend.map((b, i) => (
                      <div key={`grid-${b.date}`} className="flex flex-col justify-end">
                        <div
                          className={[
                            "w-full rounded-t",
                            i === trend.length - 1 ? "bg-green" : "bg-green-deep",
                          ].join(" ")}
                          style={{ height: `${(b.avg_bill / trendMaxRupees) * 100}%` }}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 grid h-full grid-cols-8 gap-2">
                    {trend.map((b, i) => (
                      <div key={`solar-${b.date}`} className="flex flex-col justify-end">
                        <div
                          className={[
                            "w-full rounded-t",
                            i === trend.length - 1 ? "bg-terracotta/80" : "bg-marigold",
                          ].join(" ")}
                          style={{ height: `${(b.avg_solar_bill / trendMaxRupees) * 100}%` }}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="mt-2 grid grid-cols-8 gap-2 text-[10px] text-ink-faint">
                    {trend.map((b, i) => (
                      <span
                        key={`lbl-${b.date}`}
                        className={[
                          "text-center",
                          i === trend.length - 1 ? "font-semibold text-terracotta" : "",
                        ].join(" ")}
                      >
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
            className="scroll-mt-24 rounded-card border border-ink/10 bg-paper p-5 shadow-card"
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="font-serif text-xl font-semibold text-ink">Recent Activity</h2>
                <p className="text-sm text-ink-faint">
                  Anonymised log. Phone numbers and names are never surfaced here.
                </p>
              </div>
              <span className="text-sm text-ink-faint">Last {activities.length}</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-ink/10 text-ink-faint">
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
                      <td colSpan={6} className="py-6 text-center text-ink-faint">
                        No activity yet.
                      </td>
                    </tr>
                  ) : (
                    activities.map((row) => (
                      <tr key={row.log_id} className="border-b border-ink/5 last:border-0">
                        <td className="py-3 font-medium text-ink">{row.log_id}</td>
                        <td className="py-3">{row.units_consumed}</td>
                        <td className="py-3">{rupees(row.net_bill_rupees)}</td>
                        <td className="py-3">{row.source}</td>
                        <td className="py-3">
                          <span
                            className={[
                              "inline-flex rounded-full border px-2 py-1 text-xs font-medium",
                              statusClass(row.status),
                            ].join(" ")}
                          >
                            {row.status}
                          </span>
                        </td>
                        <td className="py-3 text-ink-faint">{row.time}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div
            id="feedback"
            className="scroll-mt-24 rounded-card border border-ink/10 bg-paper p-5 shadow-card"
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="font-serif text-xl font-semibold text-ink">User Feedback</h2>
                <p className="text-sm text-ink-faint">
                  Anonymised testimonials from consented users · sample data
                </p>
              </div>
              <span className="inline-flex items-center gap-1 rounded-full border border-gold/40 bg-gold/15 px-3 py-1 text-sm text-amber-800">
                <Star size={14} className="fill-gold text-gold" />
                4.6 / 5 avg
              </span>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {DUMMY_FEEDBACK.map((fb) => (
                <div
                  key={fb.id}
                  className="flex h-full flex-col rounded-xl border border-ink/10 bg-paper-2 p-4 shadow-card"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-sm font-medium text-ink">{fb.name}</p>
                    <div className="flex items-center gap-0.5">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star
                          key={i}
                          size={14}
                          className={
                            i < fb.rating
                              ? "fill-gold text-gold"
                              : "text-ink-faint/40"
                          }
                        />
                      ))}
                    </div>
                  </div>
                  <p className="text-[11px] uppercase tracking-wider text-green-deep">
                    {fb.persona}
                  </p>
                  <p className="mt-3 flex-1 font-serif text-[15px] italic leading-relaxed text-ink-soft">
                    &ldquo;{fb.quote}&rdquo;
                  </p>
                  <p className="mt-3 text-xs text-ink-faint">{fb.time}</p>
                </div>
              ))}
            </div>
          </div>

          <div
            id="dpdpa"
            className="scroll-mt-24 rounded-card border border-ink/10 bg-paper p-5 shadow-card"
          >
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="font-serif text-xl font-semibold text-ink">DPDPA Compliance</h2>
                <p className="text-sm text-ink-faint">
                  Digital Personal Data Protection Act, 2023 - by design, not by checkbox.
                </p>
              </div>
              <span className="vm-chamfer hidden bg-bronze px-5 py-1.5 text-[11px] font-bold uppercase tracking-[0.11em] text-[#fff7ea] sm:inline-block">
                DPDPA 2023
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-green/25 bg-green/5 p-4 text-sm">
                <p className="font-semibold text-green-ink">Consent before processing</p>
                <p className="mt-1 text-ink-soft">
                  Every user sees the privacy notice in Kannada + English and must
                  reply <code className="rounded bg-cream-2 px-1 text-green-ink">START</code>.
                  Unconsented messages are never forwarded to Gemini.
                </p>
                <p className="mt-2 text-xs text-green-deep">
                  {metrics ? `${metrics.consented_users} of ${metrics.total_users}` : "-"}{" "}
                  users consented
                </p>
              </div>

              <div className="rounded-xl border border-green/25 bg-green/5 p-4 text-sm">
                <p className="font-semibold text-green-ink">Bill images never stored</p>
                <p className="mt-1 text-ink-soft">
                  The <code className="rounded bg-cream-2 px-1 text-green-ink">bills</code> schema
                  has no <code className="rounded bg-cream-2 px-1 text-green-ink">bill_image</code>,{" "}
                  <code className="rounded bg-cream-2 px-1 text-green-ink">bill_url</code>, or any
                  raw-image column. <code className="rounded bg-cream-2 px-1 text-green-ink">write_bill</code>{" "}
                  raises on any such field.
                </p>
              </div>

              <div className="rounded-xl border border-green/25 bg-green/5 p-4 text-sm">
                <p className="font-semibold text-green-ink">STOP is a hard delete</p>
                <p className="mt-1 text-ink-soft">
                  One-word opt-out. User row + cascaded bills gone immediately. No soft
                  delete, no <code className="rounded bg-cream-2 px-1 text-green-ink">deleted_at</code>{" "}
                  column, no recovery.
                </p>
              </div>

              <div className="rounded-xl border border-green/25 bg-green/5 p-4 text-sm">
                <p className="font-semibold text-green-ink">Aggregate-only dashboard</p>
                <p className="mt-1 text-ink-soft">
                  Every query on this page is <code className="rounded bg-cream-2 px-1 text-green-ink">COUNT</code>/
                  <code className="rounded bg-cream-2 px-1 text-green-ink">AVG</code>/
                  <code className="rounded bg-cream-2 px-1 text-green-ink">SUM</code> or anonymised.
                  No route surfaces phone number, consumer name, or RR number.
                </p>
              </div>
            </div>

            <p className="mt-4 text-xs text-ink-faint">
              Sources: CLAUDE.md §3 Rule 2 · tech spec §9 (DPDPA Compliance Design) ·
              PRD §3.1 M8 (Consent flow).
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
