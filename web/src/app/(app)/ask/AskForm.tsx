"use client";

import { useState, useTransition, type FormEvent } from "react";

import { Table, Td, Th } from "@/components/table";
import { Button, ErrorNotice, Panel, SectionTitle } from "@/components/ui";
import { formatNumber } from "@/lib/format";
import type { AskAnswer } from "@/lib/types";

import { AskChart, chartData } from "./AskChart";

const EXAMPLES = [
  "Revenue by month",
  "Top 10 products by revenue",
  "How many customers are in each segment?",
  "Average order value by month",
  "Active customers with over 70% churn risk who spent more than 1,000",
];

type Outcome =
  { kind: "answer"; answer: AskAnswer } | { kind: "problem"; message: string; notSetUp: boolean };

export function AskForm() {
  const [question, setQuestion] = useState("");
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [pending, startTransition] = useTransition();

  function ask(text: string) {
    const trimmed = text.trim();
    if (trimmed.length < 3) return;
    setQuestion(trimmed);
    startTransition(async () => {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      }).catch(() => null);
      if (!response) {
        setOutcome({
          kind: "problem",
          message: "Couldn't reach the server. Try again.",
          notSetUp: false,
        });
        return;
      }
      const body = await response.json().catch(() => null);
      if (response.ok && body) {
        setOutcome({ kind: "answer", answer: body as AskAnswer });
      } else {
        setOutcome({
          kind: "problem",
          message: typeof body?.detail === "string" ? body.detail : "That didn't work. Try again.",
          notSetUp: response.status === 503,
        });
      }
    });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    ask(question);
  }

  return (
    <>
      <Panel className="mt-6 p-5 sm:p-6">
        <form onSubmit={submit} className="flex flex-col gap-3">
          <label htmlFor="question" className="font-medium">
            Ask about your sales data
          </label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="For example: revenue by month in 2011"
              maxLength={500}
              className="h-11 min-w-0 flex-1 rounded-md border border-line bg-surface px-3 text-base placeholder:text-muted focus-visible:border-accent"
            />
            <Button type="submit" disabled={pending} className="h-11">
              {pending ? "Working…" : "Ask"}
            </Button>
          </div>
        </form>
        <div className="mt-4 flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => ask(example)}
              disabled={pending}
              className="rounded-full border border-line px-3 py-1 text-sm text-muted hover:border-ink hover:text-ink"
            >
              {example}
            </button>
          ))}
        </div>
        <p className="mt-4 text-sm text-muted">
          An AI writes a database query for your question. Only the question and a description of
          the tables are sent to it, never your data. The query can only read your
          organization&apos;s data, and it&apos;s shown below every answer so you can check it.
        </p>
      </Panel>

      <div aria-live="polite" className={pending ? "opacity-50 transition-opacity" : ""}>
        {pending && !outcome && (
          <p className="mt-6 text-sm text-muted">Writing and running the query…</p>
        )}
        {outcome?.kind === "problem" && (
          <Panel className="mt-6 p-5 sm:p-6">
            <SectionTitle>
              {outcome.notSetUp ? "Questions aren't set up yet" : "No answer"}
            </SectionTitle>
            <p className="mt-2 max-w-[70ch] text-muted">{outcome.message}</p>
          </Panel>
        )}
        {outcome?.kind === "answer" && <Answer answer={outcome.answer} />}
      </div>
    </>
  );
}

function Answer({ answer }: { answer: AskAnswer }) {
  const data = chartData(answer);
  const kind = answer.chart?.type;
  const single =
    kind === "number" && answer.rows.length === 1
      ? answer.rows[0].find((cell) => typeof cell === "number")
      : undefined;

  return (
    <Panel className="mt-6 p-5 sm:p-6">
      <SectionTitle>{answer.title ?? answer.question}</SectionTitle>
      <p className="mt-0.5 text-sm text-muted">&ldquo;{answer.question}&rdquo;</p>

      <div className="mt-5">
        {answer.error ? (
          <ErrorNotice>{answer.error}</ErrorNotice>
        ) : answer.rows.length === 0 ? (
          <p className="text-muted">The query ran but found nothing.</p>
        ) : single !== undefined ? (
          <p className="figure text-5xl font-semibold tracking-tight">
            {formatNumber(Number(single))}
          </p>
        ) : (kind === "bar" || kind === "line") && data ? (
          <AskChart answer={answer} data={data} />
        ) : null}
      </div>

      {!answer.error && answer.rows.length > 0 && (
        <details
          className="mt-4 text-sm"
          open={kind === "table" || (!data && single === undefined)}
        >
          <summary className="cursor-pointer text-muted hover:text-ink">Show as table</summary>
          <div className="mt-3 max-h-96 overflow-y-auto">
            <Table label="Answer">
              <thead>
                <tr>
                  {answer.columns.map((column) => (
                    <Th key={column}>{column.replaceAll("_", " ")}</Th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {answer.rows.map((row, index) => (
                  <tr key={index}>
                    {row.map((cell, column) => (
                      <Td key={column} numeric={typeof cell === "number"}>
                        {typeof cell === "number" ? formatNumber(cell) : String(cell ?? "–")}
                      </Td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
          {answer.truncated && (
            <p className="mt-2 text-muted">
              Showing the first {formatNumber(answer.rows.length)} rows.
            </p>
          )}
        </details>
      )}

      {answer.sql && (
        <div className="mt-5 border-t border-line pt-4">
          <p className="text-sm text-muted">The query that ran</p>
          <pre className="mt-2 overflow-x-auto rounded-md bg-canvas p-3 text-sm leading-relaxed whitespace-pre-wrap">
            <code>{answer.sql}</code>
          </pre>
        </div>
      )}
    </Panel>
  );
}
