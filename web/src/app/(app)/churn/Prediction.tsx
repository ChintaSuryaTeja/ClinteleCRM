import Link from "next/link";

import { riskPercent } from "@/components/customers/CustomerResults";
import { SegmentBadge } from "@/components/SegmentBadge";
import { Table, Td, Th } from "@/components/table";
import { Panel, SectionTitle } from "@/components/ui";
import { customerLabel, formatDate, formatMoney, formatNumber } from "@/lib/format";
import type { CustomerPage, ModelRun } from "@/lib/types";

const percent = (share: number) => `${Math.round(share * 100)}%`;

/** Active customers most likely to churn in the next 90 days, with the reasons. */
export function AtRisk({
  model,
  atRisk,
  currency,
}: {
  model: ModelRun | null;
  atRisk: CustomerPage;
  currency: string;
}) {
  return (
    <Panel className="mt-6 p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <SectionTitle>Most likely to churn next</SectionTitle>
        {atRisk.total > 0 && (
          <Link
            href="/segments?status=active&sort=churn_risk&min_churn_risk=50#builder"
            className="text-sm font-medium text-accent underline underline-offset-2"
          >
            Everyone at 50% risk or more
          </Link>
        )}
      </div>
      <p className="mt-0.5 text-sm text-muted">
        Active customers, by predicted chance of placing no order in the next 90 days.
      </p>

      {model === null || model.status !== "trained" ? (
        <p className="mt-4 text-sm text-muted">
          {model?.message ??
            "Predictions appear after the next import or the nightly recalculation."}
        </p>
      ) : atRisk.items.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No active customers to score.</p>
      ) : (
        <div className="mt-4">
          <Table label="Customers most likely to churn">
            <thead>
              <tr>
                <Th>Customer</Th>
                <Th numeric>Risk</Th>
                <Th>Why</Th>
                <Th>Segment</Th>
                <Th numeric>Total spent</Th>
                <Th numeric>Last order</Th>
              </tr>
            </thead>
            <tbody>
              {atRisk.items.map((customer) => (
                <tr key={customer.id} className="align-top">
                  <Td>
                    <Link
                      href={`/customers/${customer.id}`}
                      className="font-medium whitespace-nowrap underline-offset-2 hover:underline"
                    >
                      {customerLabel(customer)}
                    </Link>
                  </Td>
                  <Td numeric className="font-semibold">
                    {riskPercent(customer.churn_risk)}
                  </Td>
                  <Td className="min-w-64 text-muted">
                    {(customer.churn_reasons ?? []).join(". ")}
                  </Td>
                  <Td>
                    <SegmentBadge segment={customer.segment} />
                  </Td>
                  <Td numeric>{formatMoney(customer.total_spent, currency)}</Td>
                  <Td numeric>
                    {customer.last_order_at ? formatDate(customer.last_order_at) : "–"}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
    </Panel>
  );
}

/** How well the model did on a period it never saw, against the naive rule. */
export function ModelQuality({ model }: { model: ModelRun | null }) {
  if (
    !model ||
    model.status !== "trained" ||
    model.model_auc === null ||
    model.baseline_auc === null ||
    model.model_top10 === null ||
    model.baseline_top10 === null ||
    model.test_cutoff === null
  ) {
    return null;
  }
  const rows = [
    {
      name: "Prediction model",
      note: "Days since last order, usual ordering rhythm, number and size of orders, spending trend",
      auc: model.model_auc,
      top10: model.model_top10,
    },
    {
      name: "Simple rule",
      note: "Longest since last order is riskiest",
      auc: model.baseline_auc,
      top10: model.baseline_top10,
    },
  ];
  return (
    <Panel className="mt-6 p-5 sm:p-6">
      <SectionTitle>How good are the predictions?</SectionTitle>
      <p className="mt-1 max-w-[75ch] text-sm text-muted">
        The model was tested on {formatDate(model.test_cutoff)}: it only saw orders before that day
        and predicted who would place no order in the next 90 days. Then its guesses were checked
        against what really happened ({formatNumber(model.test_rows ?? 0)} customers,{" "}
        {percent(model.test_churn_rate ?? 0)} of whom churned).
      </p>
      <div className="mt-4">
        <Table label="Prediction quality compared with the simple rule">
          <thead>
            <tr>
              <Th>Method</Th>
              <Th
                numeric
                title="Out of 100 pairs of one churner and one stayer, how often the churner was ranked riskier"
              >
                Ranks churners higher
              </Th>
              <Th numeric>Correct among its 10% riskiest</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.name}>
                <Td>
                  <span className="font-medium">{row.name}</span>
                  <span className="block text-muted">{row.note}</span>
                </Td>
                <Td numeric>{percent(row.auc)} of the time</Td>
                <Td numeric>{percent(row.top10)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
      <p className="mt-4 text-sm text-muted">
        {model.used === "model"
          ? "The model beats the simple rule, so its scores are the ones shown."
          : "The model didn't beat the simple rule this time, so the rule's scores are shown instead."}{" "}
        &ldquo;Ranks churners higher&rdquo; is the ROC AUC: 50% would be a coin flip.
        {model.gbm_auc !== null &&
          ` A more complex model (gradient boosting) scored ${percent(model.gbm_auc)}.`}{" "}
        Retrained {formatDate(model.trained_at)} on {formatNumber(model.train_rows ?? 0)} past
        examples.
      </p>
    </Panel>
  );
}
