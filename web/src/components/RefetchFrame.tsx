"use client";

import { useRouter } from "next/navigation";
import { createContext, useContext, useTransition, type ReactNode } from "react";

type Navigate = (url: string) => void;
const NavigateContext = createContext<Navigate | null>(null);

/**
 * Wraps a screen whose filters live in the URL. When a filter changes, the
 * current content stays on screen, dimmed, until the new data arrives,
 * instead of being replaced by a loading skeleton.
 */
export function RefetchFrame({ filters, children }: { filters: ReactNode; children: ReactNode }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const navigate = (url: string) => startTransition(() => router.push(url, { scroll: false }));

  return (
    <NavigateContext.Provider value={navigate}>
      {filters}
      <div
        aria-busy={pending}
        className={`transition-opacity ${pending ? "opacity-50 motion-reduce:transition-none" : ""}`}
      >
        {children}
      </div>
    </NavigateContext.Provider>
  );
}

/** For filter controls inside a RefetchFrame: go to a new URL while keeping the frame. */
export function useFilterNavigation(): Navigate {
  const navigate = useContext(NavigateContext);
  if (!navigate) throw new Error("useFilterNavigation must be used inside <RefetchFrame>");
  return navigate;
}
