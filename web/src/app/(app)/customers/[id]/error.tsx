"use client";

import { ErrorState, PageTitle } from "@/components/ui";

export default function CustomerError({ retry }: { error: Error; retry: () => void }) {
  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Customer</PageTitle>
      <div className="mt-8">
        <ErrorState message="This customer's details couldn't be loaded." onRetry={retry} />
      </div>
    </div>
  );
}
