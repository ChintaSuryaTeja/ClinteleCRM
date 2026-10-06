"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatDate, formatNumber, formatPeriod } from "@/lib/format";
import type { AskAnswer } from "@/lib/types";

const AXIS_TEXT = { fill: "var(--muted)", fontSize: 12 };

type Point = Record<string, string | number | boolean | null>;

/** Turn rows into objects keyed by column, and check the chart's columns exist and plot numbers. */
export function chartData(answer: AskAnswer): Point[] | null {
  const chart = answer.chart;
  if (!chart || !chart.x || !chart.y) return null;
  const xIndex = answer.columns.indexOf(chart.x);
  const yIndex = answer.columns.indexOf(chart.y);
  if (xIndex === -1 || yIndex === -1 || answer.rows.length === 0) return null;
  if (!answer.rows.every((row) => typeof row[yIndex] === "number" || row[yIndex] === null)) {
    return null;
  }
  const labels = readableDates(answer.rows.map((row) => String(row[xIndex])));
  return answer.rows.map((row, index) => ({ x: labels[index], y: row[yIndex] }));
}

/** ISO dates on the axis read better as "Jan 2011" (first days of months) or "1 Jan 2011". */
function readableDates(labels: string[]): string[] {
  if (!labels.every((label) => /^\d{4}-\d{2}-\d{2}/.test(label))) return labels;
  const monthly = labels.every((label) => label.slice(8, 10) === "01");
  return labels.map((label) =>
    monthly ? formatPeriod(label.slice(0, 10), "month") : formatDate(label.slice(0, 10)),
  );
}

function value(n: unknown): string {
  return typeof n === "number" ? formatNumber(n) : String(n ?? "–");
}

/** One series, so no legend: the answer's title names it. */
export function AskChart({ answer, data }: { answer: AskAnswer; data: Point[] }) {
  const label = answer.chart?.y ?? "";
  const tooltip = (
    <Tooltip
      cursor={answer.chart?.type === "bar" ? { fill: "var(--line)", opacity: 0.35 } : undefined}
      content={({ active, payload }) => {
        const point = payload?.[0]?.payload as Point | undefined;
        if (!active || !point) return null;
        return (
          <div className="rounded-md border border-line bg-surface px-3 py-2 text-sm shadow-sm">
            <p className="font-semibold">{value(point.y)}</p>
            <p className="text-muted">{String(point.x)}</p>
            <p className="text-muted">{label.replaceAll("_", " ")}</p>
          </div>
        );
      }}
    />
  );
  const axes = (
    <>
      <CartesianGrid vertical={false} stroke="var(--line)" />
      <XAxis
        dataKey="x"
        tick={AXIS_TEXT}
        tickLine={false}
        axisLine={{ stroke: "var(--line)" }}
        minTickGap={16}
      />
      <YAxis
        tickFormatter={(n: number) => formatNumber(n, true)}
        tick={AXIS_TEXT}
        tickLine={false}
        axisLine={false}
        width={56}
      />
    </>
  );
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        {answer.chart?.type === "line" ? (
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            {axes}
            {tooltip}
            <Line
              dataKey="y"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={
                data.length <= 40
                  ? { r: 4, fill: "var(--chart-1)", stroke: "var(--surface)", strokeWidth: 2 }
                  : false
              }
              isAnimationActive={false}
            />
          </LineChart>
        ) : (
          <BarChart
            data={data}
            margin={{ top: 8, right: 0, bottom: 0, left: 0 }}
            barCategoryGap={2}
          >
            {axes}
            {tooltip}
            <Bar
              dataKey="y"
              fill="var(--chart-1)"
              radius={[4, 4, 0, 0]}
              maxBarSize={24}
              isAnimationActive={false}
            />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
