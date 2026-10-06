import { Panel, Skeleton } from "@/components/ui";

export default function ImportLoading() {
  return (
    <div className="mx-auto max-w-6xl" aria-busy="true">
      <span className="sr-only">Loading imports</span>
      <Skeleton className="h-9 w-40" />
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel className="flex flex-col gap-3 p-6">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-10 w-full" />
        </Panel>
        <Panel className="flex flex-col gap-3 p-6">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-24 w-full" />
        </Panel>
      </div>
    </div>
  );
}
