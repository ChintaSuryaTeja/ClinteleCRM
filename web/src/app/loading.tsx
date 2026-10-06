import { Skeleton } from "@/components/ui";

// Shown while the app shell itself loads (it fetches the current user first).
export default function AppLoading() {
  return (
    <div className="flex min-h-dvh items-center justify-center" aria-busy="true">
      <span className="sr-only">Loading</span>
      <Skeleton className="h-2 w-32" />
    </div>
  );
}
