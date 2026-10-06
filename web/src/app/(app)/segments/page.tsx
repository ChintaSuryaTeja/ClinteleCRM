import type { Metadata } from "next";
import Link from "next/link";

import { CustomerResults } from "@/components/customers/CustomerResults";
import { RefetchFrame } from "@/components/RefetchFrame";
import { Table, Td, Th } from "@/components/table";
import { ButtonLink, EmptyState, PageTitle, Panel, SectionTitle } from "@/components/ui";
import { formatDate, formatMoney, formatNumber } from "@/lib/format";
import { SEGMENTS, segmentColor } from "@/lib/segments";
import { getCurrentUser, getCustomers, getSegments } from "@/lib/server-api";

import { BUILDER_KEYS } from "./builder-keys";
import { SegmentBuilder } from "./SegmentBuilder";

export const metadata: Metadata = { title: "Segments" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function SegmentsPage({ searchParams }: { searchParams: SearchParams }) {
  // Keep only the parameters the API knows. "segment" may be repeated.
  const params = await searchParams;
  const query = new URLSearchParams();
  const segments = params.segment;
  for (const segment of Array.isArray(segments) ? segments : segments ? [segments] : []) {
    query.append("segment", segment);
  }
  for (const key of [...BUILDER_KEYS, "sort", "direction", "page"]) {
    const value = params[key];
    if (typeof value === "string" && value) query.set(key, value);
  }
  const filtered = query.has("segment") || BUILDER_KEYS.some((key) => query.has(key));

  const [user, overview, result] = await Promise.all([
    getCurrentUser(),
    getSegments(),
    getCustomers(query),
  ]);
  const currency = user.organization.currency;

  if (overview.customers === 0) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageTitle>Segments</PageTitle>
        <div className="mt-8">
          <EmptyState title="No segments yet">
            <p>
              Customers are sorted into segments by how recently, how often and how much they buy.
              {user.role === "admin"
                ? " Import a file of orders to see them."
                : " They appear once an admin imports a file of orders."}
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

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle>Segments</PageTitle>
      {overview.as_of && (
        <p className="mt-1 text-muted">As of your latest order, {formatDate(overview.as_of)}</p>
      )}

      <Panel className="mt-6 p-5 sm:p-6">
        <SectionTitle>Who your customers are</SectionTitle>
        <p className="mt-1 max-w-[70ch] text-sm text-muted">
          Each customer gets a score from 1 to 5 for recency (how recently they ordered), frequency
          (how often) and monetary value (how much), compared with your other customers. The scores
          decide the segment.
        </p>
        <div className="mt-4">
          <Table label="Customers and revenue by segment">
            <thead>
              <tr>
                <Th>Segment</Th>
                <Th numeric>Customers</Th>
                <Th className="w-[22%]">Share of customers</Th>
                <Th numeric>Revenue</Th>
                <Th className="w-[22%]">Share of revenue</Th>
              </tr>
            </thead>
            <tbody>
              {overview.segments.map((row) => {
                const about = SEGMENTS.find((s) => s.name === row.segment)?.about;
                return (
                  <tr key={row.segment}>
                    <Td>
                      <Link
                        href={`/segments?segment=${encodeURIComponent(row.segment)}#builder`}
                        className="inline-flex items-center gap-2 font-medium whitespace-nowrap underline-offset-2 hover:underline"
                      >
                        <span
                          aria-hidden="true"
                          className="size-2.5 rounded-full"
                          style={{ background: segmentColor(row.segment) }}
                        />
                        {row.segment}
                      </Link>
                      <span className="mt-0.5 block text-muted">{about}</span>
                    </Td>
                    <Td numeric>{formatNumber(row.customers)}</Td>
                    <Td>
                      <ShareBar share={row.customer_share} segment={row.segment} />
                    </Td>
                    <Td numeric>{formatMoney(row.revenue, currency, "whole")}</Td>
                    <Td>
                      <ShareBar share={row.revenue_share} segment={row.segment} />
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </div>
      </Panel>

      <Panel id="builder" className="mt-6 scroll-mt-6 p-5 sm:p-6">
        <SectionTitle>Build a customer list</SectionTitle>
        <p className="mt-1 mb-5 text-sm text-muted">
          Pick segments and narrow them down, then export the list.
        </p>
        <RefetchFrame
          filters={
            <SegmentBuilder key={query.toString()} query={query.toString()} currency={currency} />
          }
        >
          <div className="mt-6 border-t border-line pt-5">
            <CustomerResults
              result={result}
              query={query.toString()}
              basePath="/segments"
              currency={currency}
              filtered={filtered}
            />
          </div>
        </RefetchFrame>
      </Panel>
    </div>
  );
}

/** A thin bar in the segment's colour, with the percentage written beside it. */
function ShareBar({ share, segment }: { share: number; segment: string }) {
  const percent = share * 100;
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 rounded-full bg-canvas">
        <div
          className="h-2 rounded-full"
          style={{
            width: `${Math.max(percent, share > 0 ? 1 : 0)}%`,
            background: segmentColor(segment),
          }}
        />
      </div>
      <span className="w-12 text-right text-sm">{percent.toFixed(1)}%</span>
    </div>
  );
}
