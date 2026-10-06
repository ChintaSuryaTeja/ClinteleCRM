import { Panel, Skeleton } from "@/components/ui";

export default function ChurnLoading() {
  return (
    <div className="mx-auto max-w-6xl" aria-busy="true">
      <span className="sr-only">Loading churn</span>
      <Skeleton className="h-9 w-48" />
      <Skeleton className="mt-2 h-4 w-64" />
      <Panel className="mt-6 flex flex-col gap-3 p-5 sm:p-6">
        <Skeleton className="h-5 w-56" />
        {Array.from({ length: 8 }, (_, row) => (
          <Skeleton key={row} className="h-7 w-full" />
        ))}
      </Panel>
    </div>
  );
}
