"use client";

import { ErrorState, PageTitle } from "@/components/ui";

export default function CustomersError({ retry }: { error: Error; retry: () => void }) {
  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Customers</PageTitle>
      <div className="mt-8">
        <ErrorState
          message="The customer list couldn't be loaded. If you edited the address by hand, check the filter values."
          onRetry={retry}
        />
      </div>
    </div>
  );
}
