"use client";

import { useFilterNavigation } from "@/components/RefetchFrame";
import { Th } from "@/components/table";
import { Button } from "@/components/ui";
import { formatNumber } from "@/lib/format";

/** The current page's URL with some query parameters changed. Repeated keys (?segment=) survive. */
function withChanges(basePath: string, query: string, changes: Record<string, string>): string {
  const params = new URLSearchParams(query);
  for (const [key, value] of Object.entries(changes)) params.set(key, value);
  return `${basePath}?${params}`;
}

type Location = { basePath: string; query: string };

/** A column header that sorts by that column; clicking again flips the direction. */
export function SortHeader({
  label,
  column,
  numeric,
  basePath,
  query,
}: Location & { label: string; column: string; numeric?: boolean }) {
  const navigate = useFilterNavigation();
  const params = new URLSearchParams(query);
  const sort = params.get("sort") ?? "total_spent";
  const direction = params.get("direction") ?? "desc";
  const active = sort === column;
  // Names read A to Z first; numbers and dates read biggest or newest first.
  const firstDirection = column === "name" ? "asc" : "desc";
  const next = active ? (direction === "asc" ? "desc" : "asc") : firstDirection;

  return (
    <Th
      numeric={numeric}
      aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : undefined}
    >
      <button
        type="button"
        onClick={() =>
          navigate(withChanges(basePath, query, { sort: column, direction: next, page: "1" }))
        }
        className={`inline-flex items-center gap-1 hover:text-ink ${active ? "text-ink" : ""}`}
      >
        {label}
        <span aria-hidden="true" className={active ? "" : "invisible"}>
          {direction === "asc" ? "↑" : "↓"}
        </span>
      </button>
    </Th>
  );
}

export function Pagination({
  basePath,
  query,
  page,
  pageSize,
  total,
}: Location & { page: number; pageSize: number; total: number }) {
  const navigate = useFilterNavigation();
  const lastPage = Math.max(1, Math.ceil(total / pageSize));
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  const goTo = (target: number) => navigate(withChanges(basePath, query, { page: String(target) }));

  return (
    <nav aria-label="Pages" className="flex flex-wrap items-center justify-between gap-3 text-sm">
      <p className="text-muted">
        Showing {formatNumber(first)}–{formatNumber(last)} of {formatNumber(total)}
      </p>
      <div className="flex gap-2">
        <Button
          type="button"
          variant="secondary"
          disabled={page <= 1}
          onClick={() => goTo(page - 1)}
          className="disabled:cursor-not-allowed"
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={page >= lastPage}
          onClick={() => goTo(page + 1)}
          className="disabled:cursor-not-allowed"
        >
          Next
        </Button>
      </div>
    </nav>
  );
}
