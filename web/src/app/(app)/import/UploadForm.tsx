"use client";

import { useRouter } from "next/navigation";
import { useActionState } from "react";

import { Button, ErrorNotice } from "@/components/ui";

async function uploadFile(form: FormData): Promise<string | null> {
  let response: Response;
  try {
    response = await fetch("/api/imports", { method: "POST", body: form });
  } catch {
    return "Couldn't reach the server. Check your connection and try again.";
  }
  if (response.ok) return null;
  const body = await response.json().catch(() => null);
  return typeof body?.detail === "string"
    ? body.detail
    : "The upload didn't go through. Try again in a moment.";
}

export function UploadForm() {
  const router = useRouter();
  const [error, formAction, pending] = useActionState(async (_: string | null, form: FormData) => {
    const problem = await uploadFile(form);
    if (!problem) router.refresh(); // show the new job in the list below
    return problem;
  }, null);

  return (
    <form action={formAction} className="flex flex-col gap-4">
      {error && <ErrorNotice>{error}</ErrorNotice>}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="file" className="text-sm font-medium">
          File of orders
        </label>
        <input
          id="file"
          name="file"
          type="file"
          accept=".csv,.xlsx"
          required
          aria-describedby="file-hint"
          className="text-sm file:mr-3 file:h-10 file:rounded-md file:border file:border-line file:bg-surface file:px-4 file:font-medium file:text-ink hover:file:bg-canvas"
        />
        <p id="file-hint" className="text-sm text-muted">
          CSV (UTF-8) or Excel .xlsx, up to 50 MB. Excel files are read from the first sheet.
        </p>
      </div>
      <div>
        <Button type="submit" disabled={pending}>
          {pending ? "Uploading…" : "Upload and import"}
        </Button>
      </div>
    </form>
  );
}
