"use client";

import { ErrorState, PageTitle } from "@/components/ui";

export default function RetentionError({ retry }: { error: Error; retry: () => void }) {
  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Retention</PageTitle>
      <div className="mt-8">
        <ErrorState message="This page's numbers couldn't be loaded." onRetry={retry} />
      </div>
    </div>
  );
}
