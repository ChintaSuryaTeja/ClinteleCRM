"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Table, Td, Th } from "@/components/table";
import { formatNumber, formatPeriod } from "@/lib/format";
import type { Churn } from "@/lib/types";

type Month = Churn["months"][number];

const AXIS_TEXT = { fill: "var(--muted)", fontSize: 12 };
const percent = (rate: number) => `${(rate * 100).toFixed(1)}%`;

/**
 * Monthly churn rate as one line (no legend: the panel title names it).
 * Hovering shows the month's numbers; the same numbers are in the table below.
 */
export function ChurnChart({ months }: { months: Month[] }) {
  // Round axis ticks: every 5 percentage points (every 10 above 50%).
  const highest = Math.max(0.05, ...months.map((month) => month.rate ?? 0));
  const tickStep = highest > 0.5 ? 0.1 : 0.05;
  const top = Math.ceil(highest / tickStep - 1e-9) * tickStep;
  const ticks = Array.from({ length: Math.round(top / tickStep) + 1 }, (_, i) => i * tickStep);

  return (
    <div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={months} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis
              dataKey="month"
              tickFormatter={(month: string) => formatPeriod(month, "month")}
              tick={AXIS_TEXT}
              tickLine={false}
              axisLine={{ stroke: "var(--line)" }}
              minTickGap={24}
            />
            <YAxis
              tickFormatter={(rate: number) => `${Math.round(rate * 100)}%`}
              tick={AXIS_TEXT}
              tickLine={false}
              axisLine={false}
              width={44}
              domain={[0, top]}
              ticks={ticks}
            />
            <Tooltip
              cursor={{ stroke: "var(--muted)", strokeWidth: 1 }}
              content={({ active, payload }) => {
                const month = payload?.[0]?.payload as Month | undefined;
                if (!active || !month) return null;
                return (
                  <div className="rounded-md border border-line bg-surface px-3 py-2 text-sm shadow-sm">
                    <p className="font-semibold">
                      {month.rate === null ? "No rate" : percent(month.rate)}
                    </p>
                    <p className="text-muted">{formatPeriod(month.month, "month")}</p>
                    <p className="mt-1 text-muted">
                      {formatNumber(month.churned_customers)} of{" "}
                      {formatNumber(month.active_customers)} active customers churned
                    </p>
                  </div>
                );
              }}
            />
            <Line
              type="linear"
              dataKey="rate"
              stroke="var(--chart-1)"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              dot={{ r: 4, fill: "var(--chart-1)", stroke: "var(--surface)", strokeWidth: 2 }}
              activeDot={{ r: 5, fill: "var(--chart-1)", stroke: "var(--surface)", strokeWidth: 2 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <details className="mt-4 text-sm">
        <summary className="cursor-pointer text-muted hover:text-ink">Show as table</summary>
        <div className="mt-3">
          <Table label="Churn rate by month">
            <thead>
              <tr>
                <Th>Month</Th>
                <Th numeric>Active at start</Th>
                <Th numeric>Churned</Th>
                <Th numeric>Churn rate</Th>
              </tr>
            </thead>
            <tbody>
              {months.map((month) => (
                <tr key={month.month}>
                  <Td>{formatPeriod(month.month, "month")}</Td>
                  <Td numeric>{formatNumber(month.active_customers)}</Td>
                  <Td numeric>{formatNumber(month.churned_customers)}</Td>
                  <Td numeric>{month.rate === null ? "–" : percent(month.rate)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </details>
    </div>
  );
}
