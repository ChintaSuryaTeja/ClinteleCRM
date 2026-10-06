"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** While an import is still queued or running, reload the job list every 2 seconds. */
export function AutoRefresh({ active }: { active: boolean }) {
  const router = useRouter();
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => router.refresh(), 2000);
    return () => clearInterval(timer);
  }, [active, router]);
  return null;
}
