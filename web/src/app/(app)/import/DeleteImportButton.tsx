"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Button } from "@/components/ui";
import { formatNumber } from "@/lib/format";

type Props = { jobId: number; rowsImported: number; failed: boolean };

/** Delete asks once, in place, before anything is removed. */
export function DeleteImportButton({ jobId, rowsImported, failed }: Props) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function remove() {
    startTransition(async () => {
      const response = await fetch(`/api/imports/${jobId}`, { method: "DELETE" }).catch(() => null);
      if (response?.ok) {
        setConfirming(false);
        router.refresh();
        return;
      }
      const body = await response?.json().catch(() => null);
      setError(typeof body?.detail === "string" ? body.detail : "That didn't work. Try again.");
    });
  }

  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="font-medium text-danger underline-offset-2 hover:underline"
      >
        Delete
      </button>
    );
  }

  const question = failed
    ? "Remove this failed import from the list?"
    : rowsImported > 0
      ? `Delete the ${formatNumber(rowsImported)} rows this import added? This can't be undone.`
      : "Remove this import from the list?";

  return (
    <div role="group" aria-label="Confirm delete" className="flex max-w-xs flex-col gap-2 py-1">
      <p className="text-sm whitespace-normal">{question}</p>
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="flex gap-2">
        <Button
          type="button"
          variant="danger"
          onClick={remove}
          disabled={pending}
          className="h-8 px-3 text-sm"
        >
          {pending ? "Deleting…" : "Delete"}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => setConfirming(false)}
          disabled={pending}
          className="h-8 px-3 text-sm"
        >
          Keep it
        </Button>
      </div>
    </div>
  );
}
