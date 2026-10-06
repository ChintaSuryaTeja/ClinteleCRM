"use client";

import { ErrorState, PageTitle } from "@/components/ui";

// Shown when anything on the dashboard throws while loading.
export default function DashboardError({ retry }: { error: Error; retry: () => void }) {
  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Dashboard</PageTitle>
      <div className="mt-8">
        <ErrorState
          message="The server didn't answer in time or sent back an error."
          onRetry={retry}
        />
      </div>
    </div>
  );
}
