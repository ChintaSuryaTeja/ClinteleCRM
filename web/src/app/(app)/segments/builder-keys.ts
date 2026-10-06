/** The segment builder's filters that live in the URL. Shared by the page (server) and the form (client). */
export const BUILDER_KEYS = [
  "r_min",
  "r_max",
  "f_min",
  "f_max",
  "m_min",
  "m_max",
  "min_lifetime_value",
  "max_lifetime_value",
  "status",
  "min_churn_risk",
] as const;
