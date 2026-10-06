import type { Metadata } from "next";
import Link from "next/link";

import { ChurnStatus } from "@/components/customers/CustomerResults";
import { SegmentBadge } from "@/components/SegmentBadge";
import { Table, Td, Th } from "@/components/table";
import { ButtonLink, EmptyState, PageTitle, Panel, SectionTitle } from "@/components/ui";
import { customerLabel, formatDate, formatMoney, formatNumber } from "@/lib/format";
import { getChurn, getCurrentUser, getCustomers } from "@/lib/server-api";

import { ChurnChart } from "./ChurnChart";
import { AtRisk, ModelQuality } from "./Prediction";

export const metadata: Metadata = { title: "Churn" };

const RECENT = 20;

export default async function ChurnPage() {
  const [user, data, recent, atRisk] = await Promise.all([
    getCurrentUser(),
    getChurn(),
    getCustomers(
      new URLSearchParams({ status: "churned", sort: "churned_at", page_size: String(RECENT) }),
    ),
    getCustomers(
      new URLSearchParams({ status: "active", sort: "churn_risk", page_size: String(RECENT) }),
    ),
  ]);
  const currency = user.organization.currency;

  if (!data.as_of) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageTitle>Churn</PageTitle>
        <div className="mt-8">
          <EmptyState title="No churn history yet">
            <p>
              A customer counts as churned after 90 days without an order. This page shows how many
              churn each month.
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

  const everyone = data.churned_customers + data.active_customers;
  const facts = [
    {
      label: "Churned customers",
      value: formatNumber(data.churned_customers),
      note: `${((data.churned_customers / everyone) * 100).toFixed(1)}% of all customers`,
    },
    {
      label: "Monthly churn rate",
      value:
        data.monthly_churn_rate === null ? "–" : `${(data.monthly_churn_rate * 100).toFixed(1)}%`,
      note:
        data.monthly_churn_rate === null
          ? "Needs 90 days of history"
          : "Of active customers, over the last 12 full months",
    },
    {
      label: "Typical customer lifetime",
      value: `${(data.expected_lifetime_months ?? 0).toFixed(1)} months`,
      note: "1 ÷ monthly churn rate, at most 36. Used for lifetime value.",
    },
  ];

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Churn</PageTitle>
      <p className="mt-1 text-muted">
        As of your latest order, {formatDate(data.as_of)}. A customer churns after 90 days without
        an order.
      </p>

      <Panel className="mt-6">
        <dl className="grid divide-y divide-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          {facts.map((fact) => (
            <div key={fact.label} className="p-5 sm:p-6">
              <dt className="text-sm text-muted">{fact.label}</dt>
              <dd className="figure mt-1 text-2xl font-semibold">{fact.value}</dd>
              <dd className="mt-1 text-sm text-muted">{fact.note}</dd>
            </div>
          ))}
        </dl>
      </Panel>

      <AtRisk model={data.model} atRisk={atRisk} currency={currency} />
      <ModelQuality model={data.model} />

      <Panel className="mt-6 p-5 sm:p-6">
        <SectionTitle>Churn rate by month</SectionTitle>
        <p className="mt-0.5 mb-5 text-sm text-muted">
          Share of the customers active at the start of each month who churned during it. A month
          appears once it has ended and has 90 days of history before it.
        </p>
        {data.months.length === 0 ? (
          <p className="text-sm text-muted">
            Not enough history yet. The first month appears once there are 90 days of orders before
            it.
          </p>
        ) : (
          <ChurnChart months={data.months} />
        )}
      </Panel>

      <Panel className="mt-6 p-5 sm:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <SectionTitle>Recently churned</SectionTitle>
          {recent.total > 0 && (
            <Link
              href="/segments?status=churned&sort=churned_at#builder"
              className="text-sm font-medium text-accent underline underline-offset-2"
            >
              See all {formatNumber(recent.total)} in the segment builder
            </Link>
          )}
        </div>
        {recent.total === 0 ? (
          <p className="mt-3 text-sm text-muted">No customer has churned yet.</p>
        ) : (
          <div className="mt-4">
            <Table label="Recently churned customers">
              <thead>
                <tr>
                  <Th>Customer</Th>
                  <Th>Segment</Th>
                  <Th numeric>Orders</Th>
                  <Th numeric>Total spent</Th>
                  <Th numeric>Last order</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {recent.items.map((customer) => (
                  <tr key={customer.id}>
                    <Td>
                      <Link
                        href={`/customers/${customer.id}`}
                        className="font-medium whitespace-nowrap underline-offset-2 hover:underline"
                      >
                        {customerLabel(customer)}
                      </Link>
                    </Td>
                    <Td>
                      <SegmentBadge segment={customer.segment} />
                    </Td>
                    <Td numeric>{formatNumber(customer.orders)}</Td>
                    <Td numeric>{formatMoney(customer.total_spent, currency)}</Td>
                    <Td numeric>
                      {customer.last_order_at ? formatDate(customer.last_order_at) : "–"}
                    </Td>
                    <Td className="whitespace-nowrap">
                      <ChurnStatus customer={customer} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </Panel>
    </div>
  );
}
