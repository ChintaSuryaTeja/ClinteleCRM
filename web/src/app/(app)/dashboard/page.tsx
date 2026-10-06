import type { Metadata } from "next";

import { EmptyState, PageTitle } from "@/components/ui";
import { getCurrentUser } from "@/lib/server-api";

export const metadata: Metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const user = await getCurrentUser();

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Dashboard</PageTitle>
      <div className="mt-8">
        <EmptyState title="No sales data yet">
          {user.role === "admin" ? (
            <p>
              Import a CSV or Excel file of your orders. This page then shows revenue over time,
              average order value and your top customers.
            </p>
          ) : (
            <p>
              Once an admin at {user.organization.name} imports your sales data, this page shows
              revenue over time, average order value and your top customers.
            </p>
          )}
        </EmptyState>
      </div>
    </div>
  );
}
