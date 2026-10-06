import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import { SESSION_COOKIE, type CurrentUser } from "@/lib/session";

const apiUrl = process.env.API_URL ?? "http://localhost:8000";

/**
 * Calls the API from the Next.js server, passing along the visitor's login cookie.
 * A 401 means the session is missing or expired, so the visitor goes to /login.
 */
async function apiGet<T>(path: string): Promise<T> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const response = await fetch(`${apiUrl}${path}`, {
    headers: { cookie: `${SESSION_COOKIE}=${token}` },
    cache: "no-store",
  });
  if (response.status === 401) redirect("/login");
  if (!response.ok) throw new Error(`API request ${path} failed with status ${response.status}`);
  return response.json();
}

// cache() makes the layout and the page share one request per page load.
export const getCurrentUser = cache(() => apiGet<CurrentUser>("/auth/me"));
