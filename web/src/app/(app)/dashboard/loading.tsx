import { Panel, Skeleton } from "@/components/ui";

export default function DashboardLoading() {
  return (
    <div className="mx-auto max-w-6xl" aria-busy="true">
      <span className="sr-only">Loading dashboard</span>
      <Skeleton className="h-9 w-48" />
      <Skeleton className="mt-6 h-10 w-48" />
      <Panel className="mt-6 flex flex-col gap-3 p-6">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-14 w-64" />
      </Panel>
      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <Panel className="p-6">
          <Skeleton className="h-72 w-full" />
        </Panel>
        <Panel className="flex flex-col gap-3 p-6">
          {Array.from({ length: 6 }, (_, row) => (
            <Skeleton key={row} className="h-6 w-full" />
          ))}
        </Panel>
      </div>
    </div>
  );
}
