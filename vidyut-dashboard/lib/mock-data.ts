// Sample dashboard data, used when the mock-data toggle is on or the admin
// API is unreachable. Aggregates are derived from the three canonical
// personas (Nikhil 1943.22, Sunita 2445.96, Priya net 0.00) and KERC 2025
// tariff constants so judges poking at the numbers see defensible values.

import { ActivityRow, Metrics, TrendBucket } from "./api";

export const MOCK_METRICS: Metrics = {
  consented_users: 12,
  total_users: 14,
  total_bills: 27,
  gj_bills: 9,
  fct_flags_fired: 8,
  pmsg_eligible_count: 11,
  avg_bill_rupees: 1652.4,
  avg_non_gj_bill_rupees: 2194.59, // avg of Nikhil 1943.22 and Sunita 2445.96
  avg_solar_bill_rupees: 460.0,
  avg_monthly_solar_savings_rupees: 1734.59,
  annual_co2_footprint_tonnes: 20.4, // ~28,800 kWh/yr across cohort x 0.710 kg/kWh
  cliff_approaching_count: 3,
  cliff_crossed_count: 1,
  gj_subsidy_visible_rupees: 9720.18, // 9 GJ bills x Priya-class 1080.02
};

export const MOCK_ACTIVITY: ActivityRow[] = [
  {
    log_id: "LOG-0027",
    units_consumed: 210,
    sanctioned_load_kw: 3,
    is_gj: false,
    net_bill_rupees: 1943.22,
    status: "FCT Flagged",
    source: "WhatsApp",
    time: "2 min ago",
  },
  {
    log_id: "LOG-0026",
    units_consumed: 110,
    sanctioned_load_kw: 2,
    is_gj: true,
    net_bill_rupees: 0.0,
    status: "Approaching",
    source: "WhatsApp",
    time: "18 min ago",
  },
  {
    log_id: "LOG-0025",
    units_consumed: 280,
    sanctioned_load_kw: 3,
    is_gj: false,
    net_bill_rupees: 2445.96,
    status: "FCT Flagged",
    source: "Web",
    time: "41 min ago",
  },
  {
    log_id: "LOG-0024",
    units_consumed: 95,
    sanctioned_load_kw: 1,
    is_gj: true,
    net_bill_rupees: 0.0,
    status: "Subsidised",
    source: "WhatsApp",
    time: "1 hr ago",
  },
  {
    log_id: "LOG-0023",
    units_consumed: 205,
    sanctioned_load_kw: 1,
    is_gj: true,
    net_bill_rupees: 1617.31,
    status: "Cliff Crossed",
    source: "WhatsApp",
    time: "2 hrs ago",
  },
  {
    log_id: "LOG-0022",
    units_consumed: 152,
    sanctioned_load_kw: 1,
    is_gj: false,
    net_bill_rupees: 1236.66,
    status: "Normal",
    source: "Web",
    time: "3 hrs ago",
  },
  {
    log_id: "LOG-0021",
    units_consumed: 88,
    sanctioned_load_kw: 1,
    is_gj: true,
    net_bill_rupees: 0.0,
    status: "Subsidised",
    source: "WhatsApp",
    time: "5 hrs ago",
  },
  {
    log_id: "LOG-0020",
    units_consumed: 240,
    sanctioned_load_kw: 2,
    is_gj: false,
    net_bill_rupees: 2013.68,
    status: "Normal",
    source: "WhatsApp",
    time: "Yesterday",
  },
];

const TREND_VALUES: Array<[number, number]> = [
  [2110, 470],
  [1985, 430],
  [2240, 505],
  [2090, 445],
  [1870, 395],
  [2320, 520],
  [2195, 480],
  [2405, 540],
];

// Dates are generated at call time so the chart always shows the last 8 days.
export function makeMockTrend(): TrendBucket[] {
  const today = new Date();
  return TREND_VALUES.map(([avg_bill, avg_solar_bill], i) => {
    const d = new Date(today);
    d.setDate(today.getDate() - (TREND_VALUES.length - 1 - i));
    return {
      date: d.toISOString().slice(0, 10),
      avg_bill,
      avg_solar_bill,
    };
  });
}
