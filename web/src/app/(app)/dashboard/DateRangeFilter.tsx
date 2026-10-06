"use client";

import { useState, type FormEvent } from "react";

import { useFilterNavigation } from "@/components/RefetchFrame";
import { Button, SelectField, TextField } from "@/components/ui";
import { formatDate } from "@/lib/format";

// Presets count back from the latest order, not from today, so historical
// data (like the demo dataset) still fills the dashboard.
const PRESETS = [
  { id: "all", label: "All time", days: 0 },
  { id: "30", label: "Last 30 days", days: 30 },
  { id: "90", label: "Last 90 days", days: 90 },
  { id: "365", label: "Last 12 months", days: 365 },
];

function daysBefore(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() - days);
  return date.toISOString().slice(0, 10);
}

type Props = { dataStart: string; dataEnd: string; start: string; end: string };

export function DateRangeFilter({ dataStart, dataEnd, start, end }: Props) {
  const navigate = useFilterNavigation();

  const matching = PRESETS.find((preset) =>
    preset.days === 0
      ? start === dataStart && end === dataEnd
      : end === dataEnd && start === daysBefore(dataEnd, preset.days - 1),
  );
  const [choice, setChoice] = useState(matching?.id ?? "custom");

  function choosePreset(id: string) {
    setChoice(id);
    const preset = PRESETS.find((p) => p.id === id);
    if (!preset) return; // "custom": wait for the dates
    navigate(
      preset.days === 0
        ? "/dashboard"
        : `/dashboard?start=${daysBefore(dataEnd, preset.days - 1)}&end=${dataEnd}`,
    );
  }

  function applyCustom(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    navigate(`/dashboard?start=${form.get("start")}&end=${form.get("end")}`);
  }

  return (
    <div className="flex flex-wrap items-end gap-x-4 gap-y-3">
      <SelectField
        id="range"
        label="Date range"
        value={choice}
        onChange={(event) => choosePreset(event.target.value)}
      >
        {PRESETS.map((preset) => (
          <option key={preset.id} value={preset.id}>
            {preset.label}
          </option>
        ))}
        <option value="custom">Custom range</option>
      </SelectField>

      {choice === "custom" && (
        <form onSubmit={applyCustom} className="flex flex-wrap items-end gap-3">
          <TextField
            id="start"
            name="start"
            type="date"
            label="From"
            defaultValue={start}
            min={dataStart}
            max={dataEnd}
            required
          />
          <TextField
            id="end"
            name="end"
            type="date"
            label="To"
            defaultValue={end}
            min={dataStart}
            max={dataEnd}
            required
          />
          <Button type="submit" variant="secondary">
            Apply
          </Button>
        </form>
      )}

      <p className="pb-2.5 text-sm text-muted">
        Data runs from {formatDate(dataStart)} to {formatDate(dataEnd)}.
      </p>
    </div>
  );
}
