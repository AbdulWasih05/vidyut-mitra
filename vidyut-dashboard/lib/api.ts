// Thin fetch wrapper for the admin API served by Flask at NEXT_PUBLIC_ADMIN_API.
//
// Every request sends `Authorization: Bearer <ADMIN_PASSWORD>` using the value
// in `NEXT_PUBLIC_ADMIN_PASSWORD`. This is a demo-time secret, not a
// production one; rotate after the pitch. Wire real OAuth post-hackathon.

const API_BASE =
  process.env.NEXT_PUBLIC_ADMIN_API ?? "http://localhost:5001/admin";

const ADMIN_TOKEN = process.env.NEXT_PUBLIC_ADMIN_PASSWORD ?? "";

async function adminFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      Authorization: `Bearer ${ADMIN_TOKEN}`,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.error ?? detail;
    } catch {
      /* non-JSON body, fall through */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}

// ---------- Types ----------------------------------------------------------

export type Metrics = {
  consented_users: number;
  total_users: number;
  total_bills: number;
  gj_bills: number;
  fct_flags_fired: number;
  pmsg_eligible_count: number;
  avg_bill_rupees: number;
  avg_non_gj_bill_rupees: number;
  avg_solar_bill_rupees: number;
  avg_monthly_solar_savings_rupees: number;
  annual_co2_footprint_tonnes: number;
  cliff_approaching_count: number;
  cliff_crossed_count: number;
  gj_subsidy_visible_rupees: number;
};

export type ActivityRow = {
  log_id: string;
  units_consumed: number;
  sanctioned_load_kw: number | null;
  is_gj: boolean;
  net_bill_rupees: number;
  status: string;
  source: string;
  time: string;
};

export type TrendBucket = {
  date: string;
  avg_bill: number;
  avg_solar_bill: number;
};

// ---------- Endpoints ------------------------------------------------------

export const getMetrics = () => adminFetch<Metrics>("/metrics");
export const getActivity = (limit = 10) =>
  adminFetch<{ rows: ActivityRow[] }>(`/activity?limit=${limit}`);
export const getTrend = () => adminFetch<{ buckets: TrendBucket[] }>("/trend");
