"use client";

import { ErrorState, PageTitle } from "@/components/ui";

export default function ImportError({ retry }: { error: Error; retry: () => void }) {
  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Import</PageTitle>
      <div className="mt-8">
        <ErrorState message="The list of imports couldn't be loaded." onRetry={retry} />
      </div>
    </div>
  );
}
