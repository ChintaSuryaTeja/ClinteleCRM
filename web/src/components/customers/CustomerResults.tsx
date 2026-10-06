import Link from "next/link";

import { SegmentBadge } from "@/components/SegmentBadge";
import { Table, Td, Th } from "@/components/table";
import { customerLabel, formatDate, formatMoney, formatNumber } from "@/lib/format";
import type { CustomerPage, CustomerRow } from "@/lib/types";

import { Pagination, SortHeader } from "./TableControls";

type Props = {
  result: CustomerPage;
  /** The page's query string: filters, sort and page. */
  query: string;
  /** The page the controls navigate on, e.g. "/customers" or "/segments". */
  basePath: string;
  currency: string;
  filtered: boolean;
};

/**
 * A page of customers: count, CSV export of every match, the table and paging.
 * Shared by the Customers list and the segment builder.
 */
export function CustomerResults({ result, query, basePath, currency, filtered }: Props) {
  // The export gets the same filters and sort, but every page.
  const exportQuery = new URLSearchParams(query);
  exportQuery.delete("page");
  const location = { basePath, query };

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          {formatNumber(result.total)} {result.total === 1 ? "customer" : "customers"}
          {filtered && " match these filters"}
        </p>
        {result.total > 0 && (
          <a
            href={`/api/customers/export.csv?${exportQuery}`}
            download
            className="text-sm font-medium text-accent underline underline-offset-2"
          >
            Export {formatNumber(result.total)} to CSV
          </a>
        )}
      </div>

      {result.total === 0 ? (
        <p className="mt-6 text-muted">
          No customers match these filters. Loosen them or clear them to see everyone.
        </p>
      ) : (
        <>
          <div className="mt-4">
            <Table label="Customers">
              <thead>
                <tr>
                  <SortHeader label="Customer" column="name" {...location} />
                  <Th>Segment</Th>
                  <Th numeric title="Recency, frequency and monetary scores, each 1 to 5">
                    R F M
                  </Th>
                  <SortHeader label="Orders" column="orders" numeric {...location} />
                  <SortHeader label="Total spent" column="total_spent" numeric {...location} />
                  <SortHeader
                    label="Lifetime value"
                    column="lifetime_value"
                    numeric
                    {...location}
                  />
                  <SortHeader label="Last order" column="last_order" numeric {...location} />
                  <SortHeader label="Status" column="churned_at" {...location} />
                  <SortHeader label="Churn risk" column="churn_risk" numeric {...location} />
                </tr>
              </thead>
              <tbody>
                {result.items.map((customer) => (
                  <tr key={customer.id}>
                    <Td>
                      <Link
                        href={`/customers/${customer.id}`}
                        className="font-medium whitespace-nowrap underline-offset-2 hover:underline"
                      >
                        {customerLabel(customer)}
                      </Link>
                      {customer.email && <span className="block text-muted">{customer.email}</span>}
                    </Td>
                    <Td>
                      <SegmentBadge segment={customer.segment} />
                    </Td>
                    <Td numeric className="tracking-[0.2em]">
                      {rfm(customer)}
                    </Td>
                    <Td numeric>{formatNumber(customer.orders)}</Td>
                    <Td numeric>{formatMoney(customer.total_spent, currency)}</Td>
                    <Td numeric>
                      {customer.lifetime_value === null
                        ? "–"
                        : formatMoney(customer.lifetime_value, currency)}
                    </Td>
                    <Td numeric>
                      {customer.last_order_at ? formatDate(customer.last_order_at) : "–"}
                    </Td>
                    <Td className="whitespace-nowrap">
                      <ChurnStatus customer={customer} />
                    </Td>
                    <Td numeric title={customer.churn_reasons?.join("\n")}>
                      {riskPercent(customer.churn_risk)}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
          <div className="mt-5">
            <Pagination
              {...location}
              page={result.page}
              pageSize={result.page_size}
              total={result.total}
            />
          </div>
        </>
      )}
    </>
  );
}

/** Predicted chance of churning in the next 90 days, e.g. "82%". */
export function riskPercent(risk: number | null): string {
  return risk === null ? "–" : `${Math.round(risk * 100)}%`;
}

/** "545" for R=5, F=4, M=5. */
export function rfm(customer: CustomerRow): string {
  return customer.r_score === null
    ? "–"
    : `${customer.r_score}${customer.f_score}${customer.m_score}`;
}

export function ChurnStatus({ customer }: { customer: CustomerRow }) {
  if (customer.is_churned && customer.churned_at) {
    return <span>Churned {formatDate(customer.churned_at)}</span>;
  }
  if (customer.is_churned === false) return <span className="text-muted">Active</span>;
  return <span className="text-muted">–</span>;
}
