import type { Metadata } from "next";

import { CustomerResults } from "@/components/customers/CustomerResults";
import { RefetchFrame } from "@/components/RefetchFrame";
import { ButtonLink, EmptyState, PageTitle, Panel } from "@/components/ui";
import { getCurrentUser, getCustomers } from "@/lib/server-api";

import { CustomerFilters } from "./CustomerFilters";
import { FILTER_KEYS } from "./filter-keys";

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
  const query = new URLSearchParams(current);

  const [user, result] = await Promise.all([getCurrentUser(), getCustomers(query)]);
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
          <CustomerResults
            result={result}
            query={query.toString()}
            basePath="/customers"
            currency={currency}
            filtered={filtered}
          />
        </Panel>
      </RefetchFrame>
    </div>
  );
}
