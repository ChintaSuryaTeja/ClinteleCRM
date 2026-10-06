"use client";

import type { FormEvent } from "react";

import { useFilterNavigation } from "@/components/RefetchFrame";
import { Button, TextField } from "@/components/ui";

import { FILTER_KEYS } from "./filter-keys";

type Props = { current: Record<string, string>; currency: string };

/** Search is always visible; the rest sit behind "More filters" so phones aren't swamped. */
export function CustomerFilters({ current, currency }: Props) {
  const navigate = useFilterNavigation();
  const advancedCount = FILTER_KEYS.filter((key) => key !== "search" && current[key]).length;

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const query = new URLSearchParams();
    for (const key of FILTER_KEYS) {
      const value = String(form.get(key) ?? "").trim();
      if (value) query.set(key, value);
    }
    // Keep the sort order; go back to the first page of the new results.
    for (const key of ["sort", "direction"]) if (current[key]) query.set(key, current[key]);
    navigate(`/customers?${query}`);
  }

  return (
    <form onSubmit={apply} className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1 sm:max-w-sm">
          <TextField
            id="search"
            name="search"
            type="search"
            label="Search"
            placeholder="Name, email or customer ID"
            defaultValue={current.search}
          />
        </div>
        <Button type="submit">Apply filters</Button>
        {Object.keys(current).some((key) => (FILTER_KEYS as readonly string[]).includes(key)) && (
          <Button type="button" variant="secondary" onClick={() => navigate("/customers")}>
            Clear
          </Button>
        )}
      </div>

      <details open={advancedCount > 0} className="text-sm">
        <summary className="w-fit cursor-pointer text-muted hover:text-ink">
          More filters{advancedCount > 0 && ` (${advancedCount} on)`}
        </summary>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <TextField
            id="min_orders"
            name="min_orders"
            type="number"
            min={0}
            step={1}
            label="Orders, at least"
            defaultValue={current.min_orders}
          />
          <TextField
            id="max_orders"
            name="max_orders"
            type="number"
            min={0}
            step={1}
            label="Orders, at most"
            defaultValue={current.max_orders}
          />
          <TextField
            id="min_spent"
            name="min_spent"
            type="number"
            min={0}
            step="any"
            label={`Spent (${currency}), at least`}
            defaultValue={current.min_spent}
          />
          <TextField
            id="max_spent"
            name="max_spent"
            type="number"
            min={0}
            step="any"
            label={`Spent (${currency}), at most`}
            defaultValue={current.max_spent}
          />
          <TextField
            id="last_order_from"
            name="last_order_from"
            type="date"
            label="Last order from"
            defaultValue={current.last_order_from}
          />
          <TextField
            id="last_order_to"
            name="last_order_to"
            type="date"
            label="Last order to"
            defaultValue={current.last_order_to}
          />
        </div>
      </details>
    </form>
  );
}
