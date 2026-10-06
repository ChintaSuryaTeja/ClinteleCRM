"use client";

import type { FormEvent } from "react";

import { useFilterNavigation } from "@/components/RefetchFrame";
import { Button, SelectField, TextField } from "@/components/ui";
import { SEGMENTS, segmentColor } from "@/lib/segments";

import { BUILDER_KEYS } from "./builder-keys";

const SCORES = [
  { letter: "r", label: "Recency score" },
  { letter: "f", label: "Frequency score" },
  { letter: "m", label: "Monetary score" },
];

type Props = { query: string; currency: string };

/** Pick segments and narrow by scores, lifetime value and status. Results update below. */
export function SegmentBuilder({ query, currency }: Props) {
  const navigate = useFilterNavigation();
  const current = new URLSearchParams(query);
  const chosen = new Set(current.getAll("segment"));

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = new URLSearchParams();
    for (const segment of form.getAll("segment")) next.append("segment", String(segment));
    for (const key of BUILDER_KEYS) {
      const value = String(form.get(key) ?? "").trim();
      if (value) next.set(key, value);
    }
    for (const key of ["sort", "direction"]) {
      const value = current.get(key);
      if (value) next.set(key, value);
    }
    navigate(`/segments?${next}#builder`);
  }

  return (
    <form onSubmit={apply} className="flex flex-col gap-5">
      <fieldset>
        <legend className="mb-2 text-sm font-medium">Segments (none picked means all)</legend>
        <div className="flex flex-wrap gap-2">
          {SEGMENTS.map(({ name }) => (
            <label
              key={name}
              className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-line px-3 py-1.5 text-sm has-checked:border-ink has-checked:bg-canvas"
            >
              <input
                type="checkbox"
                name="segment"
                value={name}
                defaultChecked={chosen.has(name)}
                className="accent-[var(--accent)]"
              />
              <span
                aria-hidden="true"
                className="size-2.5 rounded-full"
                style={{ background: segmentColor(name) }}
              />
              {name}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {SCORES.map(({ letter, label }) => (
          <fieldset key={letter}>
            <legend className="mb-1.5 text-sm font-medium">{label}</legend>
            <div className="grid grid-cols-2 gap-2">
              {(["min", "max"] as const).map((end) => (
                <SelectField
                  key={end}
                  id={`${letter}_${end}`}
                  name={`${letter}_${end}`}
                  label={end === "min" ? "From" : "To"}
                  defaultValue={current.get(`${letter}_${end}`) ?? ""}
                >
                  <option value="">Any</option>
                  {[1, 2, 3, 4, 5].map((score) => (
                    <option key={score} value={score}>
                      {score}
                    </option>
                  ))}
                </SelectField>
              ))}
            </div>
          </fieldset>
        ))}
        <SelectField
          id="status"
          name="status"
          label="Status"
          defaultValue={current.get("status") ?? ""}
        >
          <option value="">Active and churned</option>
          <option value="active">Active only</option>
          <option value="churned">Churned only</option>
        </SelectField>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <TextField
          id="min_lifetime_value"
          name="min_lifetime_value"
          type="number"
          min={0}
          step="any"
          label={`Lifetime value (${currency}), at least`}
          defaultValue={current.get("min_lifetime_value") ?? ""}
        />
        <TextField
          id="max_lifetime_value"
          name="max_lifetime_value"
          type="number"
          min={0}
          step="any"
          label={`Lifetime value (${currency}), at most`}
          defaultValue={current.get("max_lifetime_value") ?? ""}
        />
        <TextField
          id="min_churn_risk"
          name="min_churn_risk"
          type="number"
          min={0}
          max={100}
          step={1}
          label="Churn risk (%), at least"
          hint="Predicted for active customers"
          defaultValue={current.get("min_churn_risk") ?? ""}
        />
      </div>

      <div className="flex flex-wrap gap-3">
        <Button type="submit">Show customers</Button>
        <Button type="button" variant="secondary" onClick={() => navigate("/segments#builder")}>
          Clear
        </Button>
      </div>
    </form>
  );
}
