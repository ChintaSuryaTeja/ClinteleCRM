import type { Metadata } from "next";
import Link from "next/link";

import { RefetchFrame } from "@/components/RefetchFrame";
import { Table, Td, Th } from "@/components/table";
import { ButtonLink, EmptyState, PageTitle, Panel, SectionTitle } from "@/components/ui";
import { customerLabel, formatDate, formatMoney, formatNumber } from "@/lib/format";
import { getCurrentUser, getDashboard } from "@/lib/server-api";
import type { Dashboard } from "@/lib/types";

import { DateRangeFilter } from "./DateRangeFilter";
import { RevenueChart } from "./RevenueChart";

export const metadata: Metadata = { title: "Dashboard" };

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const GRANULARITY_LABEL = { day: "day", week: "week", month: "month" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function DashboardPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const range: { start?: string; end?: string } = {};
  for (const key of ["start", "end"] as const) {
    const value = params[key];
    if (typeof value === "string" && ISO_DATE.test(value)) range[key] = value;
  }
  const [user, data] = await Promise.all([getCurrentUser(), getDashboard(range)]);

  if (!data.data_start || !data.data_end || !data.start || !data.end) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageTitle>Dashboard</PageTitle>
        <div className="mt-8">
          <EmptyState title="No sales data yet">
            {user.role === "admin" ? (
              <>
                <p>
                  Import a CSV or Excel file of your orders. This page then shows revenue over time,
                  average order value and your top customers.
                </p>
                <ButtonLink href="/import" className="mt-6">
                  Import sales data
                </ButtonLink>
              </>
            ) : (
              <p>
                Once an admin at {user.organization.name} imports your sales data, this page shows
                revenue over time, average order value and your top customers.
              </p>
            )}
          </EmptyState>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Dashboard</PageTitle>
      <RefetchFrame
        filters={
          <div className="mt-6">
            <DateRangeFilter
              key={`${data.start}-${data.end}`}
              dataStart={data.data_start}
              dataEnd={data.data_end}
              start={data.start}
              end={data.end}
            />
          </div>
        }
      >
        <Headline data={data} />
        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <Panel className="p-5 sm:p-6">
            <SectionTitle>Revenue by {GRANULARITY_LABEL[data.granularity]}</SectionTitle>
            <p className="mt-0.5 text-sm text-muted">
              {formatDate(data.start)} to {formatDate(data.end)}
            </p>
            <div className="mt-5">
              <RevenueChart
                series={data.series}
                granularity={data.granularity}
                currency={data.currency}
              />
            </div>
          </Panel>
          <TopCustomers data={data} />
        </div>
      </RefetchFrame>
    </div>
  );
}

/** Revenue is the one large figure; the other three support it. */
function Headline({ data }: { data: Dashboard }) {
  const supporting = [
    { label: "Orders", value: formatNumber(data.orders) },
    {
      label: "Average order value",
      value:
        data.average_order_value === null
          ? "–"
          : formatMoney(data.average_order_value, data.currency),
    },
    { label: "Customers who ordered", value: formatNumber(data.customers) },
  ];
  return (
    <Panel className="mt-6 grid lg:grid-cols-[minmax(0,1.3fr)_minmax(0,2fr)]">
      <div className="border-b border-line p-5 sm:p-6 lg:border-r lg:border-b-0">
        <p className="text-sm text-muted">Revenue</p>
        <p className="figure mt-1 text-5xl leading-none font-semibold tracking-tight sm:text-6xl">
          {formatMoney(data.revenue, data.currency, "whole")}
        </p>
      </div>
      <dl className="grid grid-cols-1 divide-y divide-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        {supporting.map((stat) => (
          <div key={stat.label} className="flex flex-col justify-end p-5 sm:p-6">
            <dt className="text-sm text-muted">{stat.label}</dt>
            <dd className="figure mt-1 text-2xl font-semibold">{stat.value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}

function TopCustomers({ data }: { data: Dashboard }) {
  return (
    <Panel className="p-5 sm:p-6">
      <SectionTitle>Top customers</SectionTitle>
      <p className="mt-0.5 text-sm text-muted">By revenue in this range</p>
      {data.top_customers.length === 0 ? (
        <p className="mt-6 text-sm text-muted">No orders in this date range.</p>
      ) : (
        <div className="mt-4">
          <Table label="Top customers by revenue">
            <thead>
              <tr>
                <Th className="w-8">#</Th>
                <Th>Customer</Th>
                <Th numeric>Orders</Th>
                <Th numeric>Revenue</Th>
              </tr>
            </thead>
            <tbody>
              {data.top_customers.map((customer, index) => (
                <tr key={customer.id}>
                  <Td className="text-muted">{index + 1}</Td>
                  <Td className="whitespace-nowrap">
                    <Link
                      href={`/customers/${customer.id}`}
                      className="font-medium underline-offset-2 hover:underline"
                    >
                      {customerLabel(customer)}
                    </Link>
                  </Td>
                  <Td numeric>{formatNumber(customer.orders)}</Td>
                  <Td numeric>{formatMoney(customer.revenue, data.currency)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
    </Panel>
  );
}
