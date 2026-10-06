/**
 * The 8 RFM segments in display order (best first), with what each means.
 * Must match SEGMENTS in api/app/segments.py.
 *
 * Each segment takes the categorical colour slot of its position, so a
 * segment has the same colour on every screen.
 */

export const SEGMENTS = [
  { name: "Champions", about: "Bought recently, buy often and spend the most" },
  { name: "Loyal", about: "Strong buyers, slightly less recent" },
  { name: "Potential loyalists", about: "Recent buyers with middling spend so far" },
  { name: "New", about: "Recent, but have bought little so far" },
  { name: "Need attention", about: "Neither recent nor strong buyers" },
  { name: "At risk", about: "Used to buy well, but have gone quiet" },
  { name: "Can't lose them", about: "Were among the best, now gone quiet" },
  { name: "Lost", about: "Long gone and never bought much" },
] as const;

export type SegmentName = (typeof SEGMENTS)[number]["name"];

export function segmentColor(name: string): string {
  const index = SEGMENTS.findIndex((segment) => segment.name === name);
  return index === -1 ? "var(--line)" : `var(--segment-${index + 1})`;
}
