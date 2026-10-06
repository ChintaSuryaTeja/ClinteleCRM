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
