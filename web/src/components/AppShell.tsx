"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

import { LogoutButton } from "@/components/LogoutButton";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Wordmark } from "@/components/Wordmark";
import type { CurrentUser } from "@/lib/session";

// Screens are added here as they are built. adminOnly items are hidden from viewers.
const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", adminOnly: false },
  { href: "/customers", label: "Customers", adminOnly: false },
  { href: "/segments", label: "Segments", adminOnly: false },
  { href: "/retention", label: "Retention", adminOnly: false },
  { href: "/churn", label: "Churn", adminOnly: false },
  { href: "/ask", label: "Ask", adminOnly: false },
  { href: "/import", label: "Import", adminOnly: true },
];

const ROLE_LABELS = { admin: "Admin", viewer: "Viewer" };

/**
 * Laptop: a fixed sidebar on the left.
 * Phone: a top bar whose Menu button opens the same sidebar as a full-screen panel.
 */
export function AppShell({ user, children }: { user: CurrentUser; children: ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="lg:grid lg:min-h-dvh lg:grid-cols-[15rem_1fr]">
      <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-line bg-surface px-4 lg:hidden">
        <Wordmark />
        <button
          type="button"
          aria-expanded={menuOpen}
          aria-controls="app-menu"
          onClick={() => setMenuOpen(!menuOpen)}
          className="rounded-md px-3 py-1.5 text-sm font-medium hover:bg-canvas"
        >
          {menuOpen ? "Close" : "Menu"}
        </button>
      </header>

      <aside
        id="app-menu"
        onKeyDown={(event) => event.key === "Escape" && closeMenu()}
        className={`${menuOpen ? "flex" : "hidden"} fixed inset-x-0 top-14 bottom-0 z-10 flex-col bg-surface lg:sticky lg:top-0 lg:flex lg:h-dvh lg:border-r lg:border-line`}
      >
        <div className="hidden px-5 pt-6 lg:block">
          <Wordmark />
        </div>

        <nav aria-label="Main" className="flex-1 px-3 py-4 lg:py-8">
          <ul className="flex flex-col gap-0.5">
            {NAV_ITEMS.filter((item) => !item.adminOnly || user.role === "admin").map((item) => {
              const active = pathname.startsWith(item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={closeMenu}
                    aria-current={active ? "page" : undefined}
                    className={`block rounded-md px-3 py-2 ${
                      active
                        ? "bg-canvas font-medium text-ink shadow-[inset_3px_0_0_var(--accent)]"
                        : "text-muted hover:text-ink"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="flex flex-col gap-4 border-t border-line px-5 py-5">
          <div className="min-w-0">
            <p className="truncate font-medium">{user.organization.name}</p>
            <p className="truncate text-sm text-muted">{user.email}</p>
            <p className="text-sm text-muted">{ROLE_LABELS[user.role]}</p>
          </div>
          <ThemeToggle />
          <div>
            <LogoutButton />
          </div>
        </div>
      </aside>

      <main className="min-w-0 px-4 py-6 sm:px-8 lg:px-12 lg:py-10">{children}</main>
    </div>
  );
}
