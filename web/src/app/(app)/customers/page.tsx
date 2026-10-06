import type { Metadata } from "next";
import Link from "next/link";

import { RefetchFrame } from "@/components/RefetchFrame";
import { Table, Td, Th } from "@/components/table";
import { ButtonLink, EmptyState, PageTitle, Panel } from "@/components/ui";
import { customerLabel, formatDate, formatMoney, formatNumber } from "@/lib/format";
import { getCurrentUser, getCustomers } from "@/lib/server-api";

import { CustomerFilters } from "./CustomerFilters";
import { FILTER_KEYS } from "./filter-keys";
import { Pagination, SortHeader } from "./TableControls";

export const metadata: Metadata = { title: "Customers" };

const ALLOWED_KEYS = [...FILTER_KEYS, "sort", "direction", "page"];

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function CustomersPage({ searchParams }: { searchParams: SearchParams }) {
  // Only pass on the query parameters the API knows, as plain strings.
  const params = await searchParams;
  const current: Record<string, string> = {};
  for (const key of ALLOWED_KEYS) {
    const value = params[key];
    if (typeof value === "string" && value) current[key] = value;
  }
  const filtered = FILTER_KEYS.some((key) => current[key]);

  const [user, result] = await Promise.all([
    getCurrentUser(),
    getCustomers(new URLSearchParams(current)),
  ]);
  const currency = user.organization.currency;

  if (result.total === 0 && !filtered) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageTitle>Customers</PageTitle>
        <div className="mt-8">
          <EmptyState title="No customers yet">
            {user.role === "admin" ? (
              <>
                <p>Customers appear here once you import a file of orders.</p>
                <ButtonLink href="/import" className="mt-6">
                  Import sales data
                </ButtonLink>
              </>
            ) : (
              <p>Customers appear here once an admin imports a file of orders.</p>
            )}
          </EmptyState>
        </div>
      </div>
    );
  }

  // The export gets the same filters and sort as the list, but every page.
  const exportQuery = new URLSearchParams(current);
  exportQuery.delete("page");

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Customers</PageTitle>
      <RefetchFrame
        filters={
          <div className="mt-6">
            <CustomerFilters key={JSON.stringify(current)} current={current} currency={currency} />
          </div>
        }
      >
        <Panel className="mt-6 p-5 sm:p-6">
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
                      <SortHeader label="Customer" column="name" current={current} />
                      <SortHeader label="Orders" column="orders" current={current} numeric />
                      <SortHeader
                        label="Total spent"
                        column="total_spent"
                        current={current}
                        numeric
                      />
                      <Th numeric>First order</Th>
                      <SortHeader
                        label="Last order"
                        column="last_order"
                        current={current}
                        numeric
                      />
                    </tr>
                  </thead>
                  <tbody>
                    {result.items.map((customer) => (
                      <tr key={customer.id}>
                        <Td>
                          <Link
                            href={`/customers/${customer.id}`}
                            className="font-medium underline-offset-2 hover:underline"
                          >
                            {customerLabel(customer)}
                          </Link>
                          {customer.email && (
                            <span className="block text-muted">{customer.email}</span>
                          )}
                        </Td>
                        <Td numeric>{formatNumber(customer.orders)}</Td>
                        <Td numeric>{formatMoney(customer.total_spent, currency)}</Td>
                        <Td numeric>
                          {customer.first_order_at ? formatDate(customer.first_order_at) : "–"}
                        </Td>
                        <Td numeric>
                          {customer.last_order_at ? formatDate(customer.last_order_at) : "–"}
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
              <div className="mt-5">
                <Pagination
                  current={current}
                  page={result.page}
                  pageSize={result.page_size}
                  total={result.total}
                />
              </div>
            </>
          )}
        </Panel>
      </RefetchFrame>
    </div>
  );
}
