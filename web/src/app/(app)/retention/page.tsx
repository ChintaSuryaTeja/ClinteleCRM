import type { Metadata } from "next";

import { ButtonLink, EmptyState, PageTitle, Panel } from "@/components/ui";
import { formatDate, formatNumber } from "@/lib/format";
import { getCurrentUser, getRetention } from "@/lib/server-api";

export const metadata: Metadata = { title: "Retention" };

// Lower edges of the 7 shading steps. Most retention values sit below 50%,
// so the steps are finer there.
const STEPS = [0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5];
const STEP_LABELS = ["under 5%", "5–10%", "10–20%", "20–30%", "30–40%", "40–50%", "50% or more"];

function step(rate: number): number {
  let found = 1;
  STEPS.forEach((low, index) => {
    if (rate >= low) found = index + 1;
  });
  return found;
}

function monthLabel(iso: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${iso}T00:00:00Z`));
}

export default async function RetentionPage() {
  const [user, data] = await Promise.all([getCurrentUser(), getRetention()]);

  if (!data.as_of || data.cohorts.length === 0) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageTitle>Retention</PageTitle>
        <div className="mt-8">
          <EmptyState title="No cohorts yet">
            <p>
              This page groups customers by the month they first ordered and shows how many keep
              coming back.
              {user.role === "admin"
                ? " Import a file of orders to see it."
                : " It fills in once an admin imports a file of orders."}
            </p>
            {user.role === "admin" && (
              <ButtonLink href="/import" className="mt-6">
                Import sales data
              </ButtonLink>
            )}
          </EmptyState>
        </div>
      </div>
    );
  }

  const longest = Math.max(...data.cohorts.map((cohort) => cohort.rates.length));
  const laterMonths = Array.from({ length: longest - 1 }, (_, index) => index + 1);

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Retention</PageTitle>
      <p className="mt-1 text-muted">As of your latest order, {formatDate(data.as_of)}</p>

      <Panel className="mt-6 p-5 sm:p-6">
        <p className="max-w-[70ch] text-sm text-muted">
          Each row is the customers who first ordered in that month. Each cell is the share of them
          who ordered again that many months later. The most recent month is still in progress, so
          its numbers can still rise.
        </p>

        <div className="mt-5 overflow-x-auto">
          <table
            aria-label="Retention by first-order month"
            className="border-separate border-spacing-0.5 text-sm"
          >
            <thead>
              <tr>
                <th
                  scope="col"
                  className="px-2 py-1.5 text-left font-medium whitespace-nowrap text-muted"
                >
                  First order
                </th>
                <th
                  scope="col"
                  className="px-2 py-1.5 text-right font-medium whitespace-nowrap text-muted"
                >
                  Customers
                </th>
                {laterMonths.map((month) => (
                  <th
                    key={month}
                    scope="col"
                    className="min-w-12 px-1 py-1.5 text-center font-medium text-muted"
                  >
                    <span className="sr-only">Month </span>
                    {month}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.cohorts.map((cohort) => (
                <tr key={cohort.cohort_month}>
                  <th scope="row" className="px-2 py-1.5 text-left font-medium whitespace-nowrap">
                    {monthLabel(cohort.cohort_month)}
                  </th>
                  <td className="px-2 py-1.5 text-right">{formatNumber(cohort.size)}</td>
                  {laterMonths.map((month) => {
                    const rate = cohort.rates[month];
                    if (rate === undefined) return <td key={month} />;
                    return (
                      <td
                        key={month}
                        className={`heat-${step(rate)} rounded-sm px-1 py-1.5 text-center`}
                        title={`${formatNumber(cohort.customers[month])} of ${formatNumber(cohort.size)} customers ordered ${month} ${month === 1 ? "month" : "months"} later`}
                      >
                        {Math.round(rate * 100)}%
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-muted">Months after the first order</p>

        <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
          <span>Share who ordered again:</span>
          {STEP_LABELS.map((label, index) => (
            <span key={label} className="inline-flex items-center gap-1.5">
              <span aria-hidden="true" className={`heat-${index + 1} size-3 rounded-sm`} />
              {label}
            </span>
          ))}
        </div>
      </Panel>
    </div>
  );
}
