"use client";

import { useFilterNavigation } from "@/components/RefetchFrame";
import { Th } from "@/components/table";
import { Button } from "@/components/ui";
import { formatNumber } from "@/lib/format";

type Query = Record<string, string>;

function withChanges(current: Query, changes: Query): string {
  const query = new URLSearchParams({ ...current, ...changes });
  return `/customers?${query}`;
}

/** A column header that sorts by that column; clicking again flips the direction. */
export function SortHeader({
  label,
  column,
  current,
  numeric,
}: {
  label: string;
  column: string;
  current: Query;
  numeric?: boolean;
}) {
  const navigate = useFilterNavigation();
  const sort = current.sort ?? "total_spent";
  const direction = current.direction ?? "desc";
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
        onClick={() => navigate(withChanges(current, { sort: column, direction: next, page: "1" }))}
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
  current,
  page,
  pageSize,
  total,
}: {
  current: Query;
  page: number;
  pageSize: number;
  total: number;
}) {
  const navigate = useFilterNavigation();
  const lastPage = Math.max(1, Math.ceil(total / pageSize));
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

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
          onClick={() => navigate(withChanges(current, { page: String(page - 1) }))}
          className="disabled:cursor-not-allowed"
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={page >= lastPage}
          onClick={() => navigate(withChanges(current, { page: String(page + 1) }))}
          className="disabled:cursor-not-allowed"
        >
          Next
        </Button>
      </div>
    </nav>
  );
}
