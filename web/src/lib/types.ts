/** Shapes of API responses. They mirror api/app/schemas.py. */

export type Granularity = "day" | "week" | "month";

export type Dashboard = {
  currency: string;
  data_start: string | null;
  data_end: string | null;
  start: string | null;
  end: string | null;
  revenue: number;
  orders: number;
  average_order_value: number | null;
  customers: number;
  granularity: Granularity;
  series: { period: string; revenue: number; orders: number; average_order_value: number | null }[];
  top_customers: {
    id: number;
    external_id: string;
    name: string | null;
    revenue: number;
    orders: number;
  }[];
};

export type CustomerRow = {
  id: number;
  external_id: string;
  name: string | null;
  email: string | null;
  orders: number;
  total_spent: number;
  first_order_at: string | null;
  last_order_at: string | null;
  segment: string | null;
  r_score: number | null;
  f_score: number | null;
  m_score: number | null;
  lifetime_value: number | null;
  is_churned: boolean | null;
  churned_at: string | null;
  churn_risk: number | null;
  churn_reasons: string[] | null;
};

export type CustomerPage = { total: number; page: number; page_size: number; items: CustomerRow[] };

export type CustomerDetail = CustomerRow & {
  average_order_value: number | null;
  recent_orders: {
    id: number;
    external_id: string;
    ordered_at: string;
    total_amount: number;
    items: number;
  }[];
};

export type ImportJob = {
  id: number;
  filename: string;
  status: "queued" | "running" | "succeeded" | "failed" | "deleting";
  rows_imported: number;
  rows_rejected: number;
  rows_skipped: number;
  failure_reason: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type SegmentsOverview = {
  as_of: string | null;
  currency: string;
  customers: number;
  revenue: number;
  segments: {
    segment: string;
    customers: number;
    revenue: number;
    customer_share: number;
    revenue_share: number;
  }[];
};

export type Retention = {
  as_of: string | null;
  cohorts: { cohort_month: string; size: number; customers: number[]; rates: number[] }[];
};

export type Churn = {
  as_of: string | null;
  monthly_churn_rate: number | null;
  expected_lifetime_months: number | null;
  churned_customers: number;
  active_customers: number;
  months: {
    month: string;
    active_customers: number;
    churned_customers: number;
    rate: number | null;
  }[];
  model: ModelRun | null;
};

export type ModelRun = {
  trained_at: string;
  status: "trained" | "not_enough_data";
  message: string | null;
  used: "model" | "baseline" | null;
  test_cutoff: string | null;
  train_rows: number | null;
  test_rows: number | null;
  test_churn_rate: number | null;
  model_auc: number | null;
  baseline_auc: number | null;
  gbm_auc: number | null;
  model_top10: number | null;
  baseline_top10: number | null;
  scored_customers: number | null;
};

export type AskAnswer = {
  question: string;
  title: string | null;
  sql: string | null;
  chart: { type: "bar" | "line" | "number" | "table"; x: string | null; y: string | null } | null;
  columns: string[];
  rows: (string | number | boolean | null)[][];
  truncated: boolean;
  error: string | null;
};
