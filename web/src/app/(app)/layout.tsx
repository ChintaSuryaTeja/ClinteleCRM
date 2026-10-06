import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { getCurrentUser } from "@/lib/server-api";

/** Every logged-in screen sits inside this shell. */
export default async function AppLayout({ children }: { children: ReactNode }) {
  const user = await getCurrentUser();
  return <AppShell user={user}>{children}</AppShell>;
}
