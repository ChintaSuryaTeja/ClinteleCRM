import { Panel, Skeleton } from "@/components/ui";

export default function DashboardLoading() {
  return (
    <div className="mx-auto max-w-6xl" aria-busy="true">
      <span className="sr-only">Loading dashboard</span>
      <Skeleton className="h-9 w-48" />
      <Panel className="mt-8 flex flex-col gap-3 px-6 py-10 sm:px-10">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-full max-w-[60ch]" />
        <Skeleton className="h-4 w-2/3 max-w-[40ch]" />
      </Panel>
    </div>
  );
}
