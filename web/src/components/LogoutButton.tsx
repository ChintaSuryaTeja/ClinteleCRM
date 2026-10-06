"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { postJson } from "@/lib/client-api";

export function LogoutButton() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function logOut() {
    startTransition(async () => {
      await postJson("/auth/logout");
      router.replace("/login");
      router.refresh();
    });
  }

  return (
    <button
      type="button"
      onClick={logOut}
      disabled={pending}
      className="text-sm font-medium text-muted underline-offset-2 hover:text-ink hover:underline"
    >
      {pending ? "Logging out…" : "Log out"}
    </button>
  );
}
