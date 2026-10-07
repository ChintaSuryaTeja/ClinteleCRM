"use client";

import { useTransition } from "react";

import { postJson } from "@/lib/client-api";

export function LogoutButton() {
  const [pending, startTransition] = useTransition();

  function logOut() {
    startTransition(async () => {
      await postJson("/auth/logout");
      // A full page load, not a client-side navigation: Next.js may have cached
      // pages fetched while the visitor was logged out (or in), which would
      // show the wrong page now that the login has changed.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- deliberate full load (see above)
      window.location.assign("/login");
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
