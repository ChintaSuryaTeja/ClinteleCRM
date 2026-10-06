import type { Metadata } from "next";
import Link from "next/link";

import { riskPercent } from "@/components/customers/CustomerResults";
import { SegmentBadge } from "@/components/SegmentBadge";
import { Table, Td, Th } from "@/components/table";
import { PageTitle, Panel, SectionTitle } from "@/components/ui";
import { customerLabel, formatDate, formatMoney, formatNumber } from "@/lib/format";
import { getCurrentUser, getCustomer } from "@/lib/server-api";

type Params = Promise<{ id: string }>;

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const customer = await getCustomer((await params).id);
  return { title: customerLabel(customer) };
}

/** Read-only: customers are data from imports, not accounts anyone edits here. */
export default async function CustomerPage({ params }: { params: Params }) {
  const { id } = await params;
  const [user, customer] = await Promise.all([getCurrentUser(), getCustomer(id)]);
  const currency = user.organization.currency;

  const facts = [
    { label: "Total spent", value: formatMoney(customer.total_spent, currency) },
    { label: "Orders", value: formatNumber(customer.orders) },
    {
      label: "Average order value",
      value:
        customer.average_order_value === null
          ? "–"
          : formatMoney(customer.average_order_value, currency),
    },
    {
      label: "Lifetime value",
      value:
        customer.lifetime_value === null ? "–" : formatMoney(customer.lifetime_value, currency),
    },
    {
      label: "First order",
      value: customer.first_order_at ? formatDate(customer.first_order_at) : "–",
    },
    {
      label: "Last order",
      value: customer.last_order_at ? formatDate(customer.last_order_at) : "–",
    },
  ];

  return (
    <div className="mx-auto max-w-6xl">
      <Link href="/customers" className="text-sm text-muted underline-offset-2 hover:underline">
        All customers
      </Link>
      <div className="mt-2">
        <PageTitle>{customerLabel(customer)}</PageTitle>
        <p className="mt-1 text-muted">Customer ID {customer.external_id}</p>
        {customer.email && <p className="text-muted">{customer.email}</p>}
      </div>

      {customer.segment && (
        <Panel className="mt-6 flex flex-wrap items-center gap-x-8 gap-y-3 p-5">
          <div>
            <p className="text-sm text-muted">Segment</p>
            <p className="mt-1 font-medium">
              <SegmentBadge segment={customer.segment} />
            </p>
          </div>
          <div>
            <p className="text-sm text-muted">Scores, 1 to 5</p>
            <p className="mt-1">
              Recency {customer.r_score}, frequency {customer.f_score}, monetary {customer.m_score}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted">Status</p>
            <p className="mt-1">
              {customer.is_churned && customer.churned_at
                ? `Churned on ${formatDate(customer.churned_at)}, 90 days after their last order`
                : "Active: ordered in the last 90 days"}
            </p>
          </div>
          {customer.churn_risk !== null && (
            <div>
              <p className="text-sm text-muted">Churn risk, next 90 days</p>
              <p className="mt-1 font-medium">{riskPercent(customer.churn_risk)}</p>
            </div>
          )}
        </Panel>
      )}

      {customer.churn_reasons && customer.churn_reasons.length > 0 && (
        <Panel className="mt-6 p-5">
          <p className="text-sm text-muted">Why the risk is high</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {customer.churn_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </Panel>
      )}

      <Panel className="mt-6">
        <dl className="grid grid-cols-2 divide-line sm:grid-cols-3 lg:grid-cols-6 lg:divide-x">
          {facts.map((fact) => (
            <div key={fact.label} className="p-5">
              <dt className="text-sm text-muted">{fact.label}</dt>
              <dd className="figure mt-1 text-xl font-semibold">{fact.value}</dd>
            </div>
          ))}
        </dl>
      </Panel>

      <Panel className="mt-6 p-5 sm:p-6">
        <SectionTitle>Orders</SectionTitle>
        <p className="mt-0.5 text-sm text-muted">
          {customer.orders > customer.recent_orders.length
            ? `The latest ${customer.recent_orders.length} of ${formatNumber(customer.orders)}, newest first`
            : "Newest first"}
        </p>
        <div className="mt-4">
          <Table label="Orders">
            <thead>
              <tr>
                <Th>Date</Th>
                <Th>Order ID</Th>
                <Th numeric>Items</Th>
                <Th numeric>Total</Th>
              </tr>
            </thead>
            <tbody>
              {customer.recent_orders.map((order) => (
                <tr key={order.id}>
                  <Td className="whitespace-nowrap">{formatDate(order.ordered_at)}</Td>
                  <Td>{order.external_id}</Td>
                  <Td numeric>{formatNumber(order.items)}</Td>
                  <Td numeric>{formatMoney(order.total_amount, currency)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </Panel>
    </div>
  );
}
