import "server-only";

import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { cache } from "react";

import { SESSION_COOKIE, type CurrentUser } from "@/lib/session";
import type {
  Churn,
  CustomerDetail,
  CustomerPage,
  Dashboard,
  ImportJob,
  Retention,
  SegmentsOverview,
} from "@/lib/types";

const apiUrl = process.env.API_URL ?? "http://localhost:8000";

/**
 * Calls the API from the Next.js server, passing along the visitor's login cookie.
 * 401 (session missing or expired) sends the visitor to /login; 404 shows the
 * page's not-found screen. Any other failure throws, which shows the error screen.
 */
async function apiGet<T>(path: string): Promise<T> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const response = await fetch(`${apiUrl}${path}`, {
    headers: { cookie: `${SESSION_COOKIE}=${token}` },
    cache: "no-store",
  });
  if (response.status === 401) redirect("/login");
  if (response.status === 404) notFound();
  if (!response.ok) throw new Error(`API request ${path} failed with status ${response.status}`);
  return response.json();
}

// cache() makes the layout and the page share one request per page load.
export const getCurrentUser = cache(() => apiGet<CurrentUser>("/auth/me"));

export function getDashboard(range: { start?: string; end?: string }) {
  return apiGet<Dashboard>(`/dashboard?${new URLSearchParams(range)}`);
}

export function getCustomers(query: URLSearchParams) {
  return apiGet<CustomerPage>(`/customers?${query}`);
}

export function getCustomer(id: string) {
  if (!/^\d+$/.test(id)) notFound();
  return apiGet<CustomerDetail>(`/customers/${encodeURIComponent(id)}`);
}

export function getImports() {
  return apiGet<ImportJob[]>("/imports");
}

export function getSegments() {
  return apiGet<SegmentsOverview>("/segments");
}

export function getRetention() {
  return apiGet<Retention>("/retention");
}

export function getChurn() {
  return apiGet<Churn>("/churn");
}
