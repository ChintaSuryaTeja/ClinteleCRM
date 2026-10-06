import { Panel, Skeleton } from "@/components/ui";

export default function CustomersLoading() {
  return (
    <div className="mx-auto max-w-6xl" aria-busy="true">
      <span className="sr-only">Loading customers</span>
      <Skeleton className="h-9 w-48" />
      <Skeleton className="mt-6 h-10 w-full max-w-sm" />
      <Panel className="mt-6 flex flex-col gap-3 p-5 sm:p-6">
        <Skeleton className="h-4 w-40" />
        {Array.from({ length: 8 }, (_, row) => (
          <Skeleton key={row} className="h-6 w-full" />
        ))}
      </Panel>
    </div>
  );
}
