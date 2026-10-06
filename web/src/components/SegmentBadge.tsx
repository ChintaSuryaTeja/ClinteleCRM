import { segmentColor } from "@/lib/segments";

/** A segment's colour dot beside its name. The name carries the meaning; the dot links it to charts. */
export function SegmentBadge({ segment }: { segment: string | null }) {
  if (!segment) return <span className="text-muted">–</span>;
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span
        aria-hidden="true"
        className="size-2.5 shrink-0 rounded-full"
        style={{ background: segmentColor(segment) }}
      />
      {segment}
    </span>
  );
}
