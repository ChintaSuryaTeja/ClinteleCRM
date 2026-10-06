"use client";

import { ErrorState } from "@/components/ui";

// Catches errors outside a screen's own error page, e.g. when the app shell
// cannot load the current user because the API is down.
export default function AppError({ retry }: { error: Error; retry: () => void }) {
  return (
    <div className="mx-auto max-w-xl px-4 py-16">
      <ErrorState message="Clientele couldn't reach its server." onRetry={retry} />
    </div>
  );
}
