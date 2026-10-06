import type { Metadata } from "next";

import { PageTitle } from "@/components/ui";

import { AskForm } from "./AskForm";

export const metadata: Metadata = { title: "Ask" };

export default function AskPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Ask</PageTitle>
      <p className="mt-1 text-muted">Questions in plain English, answered from your sales data.</p>
      <AskForm />
    </div>
  );
}
