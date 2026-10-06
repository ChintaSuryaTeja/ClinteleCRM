/** Number and date formatting, so every screen shows values the same way. */

const LOCALE = "en-GB";

/**
 * exact:   £1,234.50  (tables, tooltips)
 * whole:   £1,235     (large headline figures)
 * compact: £1.2K      (chart axes)
 */
export function formatMoney(
  value: number,
  currency: string,
  style: "exact" | "whole" | "compact" = "exact",
): string {
  return new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency,
    notation: style === "compact" ? "compact" : "standard",
    minimumFractionDigits: style === "exact" ? 2 : 0,
    maximumFractionDigits: style === "exact" ? 2 : style === "compact" ? 1 : 0,
  }).format(value);
}

export function formatNumber(value: number, compact = false): string {
  return new Intl.NumberFormat(LOCALE, {
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(value);
}

/** "2024-03-01" or an ISO timestamp -> "1 Mar 2024". Dates are shown in UTC, like the metrics. */
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat(LOCALE, {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso));
}

/** Label for a chart period: "1 Mar" for days and weeks, "Mar 2024" for months. */
export function formatPeriod(iso: string, granularity: "day" | "week" | "month"): string {
  const options: Intl.DateTimeFormatOptions =
    granularity === "month"
      ? { month: "short", year: "numeric", timeZone: "UTC" }
      : { day: "numeric", month: "short", timeZone: "UTC" };
  return new Intl.DateTimeFormat(LOCALE, options).format(new Date(`${iso}T00:00:00Z`));
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat(LOCALE, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

/** Customers in some datasets have no name; fall back to their ID. */
export function customerLabel(customer: { name: string | null; external_id: string }): string {
  return customer.name ?? `Customer ${customer.external_id}`;
}
