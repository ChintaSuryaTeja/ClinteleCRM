/** The customer-list filters that live in the URL. Shared by the page (server) and the form (client). */
export const FILTER_KEYS = [
  "search",
  "min_orders",
  "max_orders",
  "min_spent",
  "max_spent",
  "last_order_from",
  "last_order_to",
] as const;
