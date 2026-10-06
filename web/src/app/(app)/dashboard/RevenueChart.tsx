"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Table, Td, Th } from "@/components/table";
import { formatMoney, formatNumber, formatPeriod } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

type Point = Dashboard["series"][number];
type Props = { series: Point[]; granularity: Dashboard["granularity"]; currency: string };

const AXIS_TEXT = { fill: "var(--muted)", fontSize: 12 };

/**
 * Revenue per day, week or month as columns: one series, so no legend (the
 * panel title names it). Hovering a column shows its numbers; the same numbers
 * are in the table underneath, so nothing depends on hovering.
 */
export function RevenueChart({ series, granularity, currency }: Props) {
  return (
    <div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={series}
            margin={{ top: 8, right: 0, bottom: 0, left: 0 }}
            barCategoryGap={2}
          >
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis
              dataKey="period"
              tickFormatter={(period: string) => formatPeriod(period, granularity)}
              tick={AXIS_TEXT}
              tickLine={false}
              axisLine={{ stroke: "var(--line)" }}
              minTickGap={24}
            />
            <YAxis
              tickFormatter={(value: number) => formatMoney(value, currency, "compact")}
              tick={AXIS_TEXT}
              tickLine={false}
              axisLine={false}
              width={64}
            />
            <Tooltip
              cursor={{ fill: "var(--line)", opacity: 0.35 }}
              content={({ active, payload }) => (
                <ChartTooltip
                  active={active}
                  point={payload?.[0]?.payload as Point | undefined}
                  granularity={granularity}
                  currency={currency}
                />
              )}
            />
            <Bar
              dataKey="revenue"
              name="Revenue"
              fill="var(--chart-1)"
              radius={[4, 4, 0, 0]}
              maxBarSize={24}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <details className="mt-4 text-sm">
        <summary className="cursor-pointer text-muted hover:text-ink">Show as table</summary>
        <div className="mt-3 max-h-80 overflow-y-auto">
          <Table label="Revenue by period">
            <thead>
              <tr>
                <Th>Period starting</Th>
                <Th numeric>Revenue</Th>
                <Th numeric>Orders</Th>
                <Th numeric>Average order</Th>
              </tr>
            </thead>
            <tbody>
              {series.map((point) => (
                <tr key={point.period}>
                  <Td>{formatPeriod(point.period, granularity)}</Td>
                  <Td numeric>{formatMoney(point.revenue, currency)}</Td>
                  <Td numeric>{formatNumber(point.orders)}</Td>
                  <Td numeric>
                    {point.average_order_value === null
                      ? "–"
                      : formatMoney(point.average_order_value, currency)}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </details>
    </div>
  );
}

type TooltipProps = {
  active?: boolean;
  point?: Point;
  granularity: Props["granularity"];
  currency: string;
};

function ChartTooltip({ active, point, granularity, currency }: TooltipProps) {
  if (!active || !point) return null;
  const prefix = granularity === "week" ? "Week of " : "";
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2 text-sm shadow-sm">
      {/* The value leads; the period is secondary. */}
      <p className="font-semibold">{formatMoney(point.revenue, currency)}</p>
      <p className="text-muted">
        {prefix}
        {formatPeriod(point.period, granularity)}
      </p>
      <p className="mt-1 text-muted">
        {formatNumber(point.orders)} orders
        {point.average_order_value !== null &&
          `, ${formatMoney(point.average_order_value, currency)} average`}
      </p>
    </div>
  );
}
