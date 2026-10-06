"use client";

import { useEffect, useSyncExternalStore } from "react";

type Theme = "system" | "light" | "dark";
const OPTIONS: { value: Theme; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];
const CHANGE_EVENT = "themechange";

function readSaved(): Theme {
  try {
    const saved = localStorage.getItem("theme");
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

function apply(theme: Theme) {
  const dark =
    theme === "dark" || (theme === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

function subscribe(onChange: () => void) {
  window.addEventListener(CHANGE_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** Lets the user pick light, dark, or follow the system setting. The choice is remembered on this device. */
export function ThemeToggle() {
  // Reads the saved choice from localStorage and re-renders when it changes.
  // On the server there is no localStorage, so it renders "system" first.
  const theme = useSyncExternalStore(subscribe, readSaved, () => "system" as Theme);

  // While following the system, react when the operating system switches modes.
  useEffect(() => {
    if (theme !== "system") return;
    const query = matchMedia("(prefers-color-scheme: dark)");
    const follow = () => apply("system");
    query.addEventListener("change", follow);
    return () => query.removeEventListener("change", follow);
  }, [theme]);

  function choose(next: Theme) {
    try {
      if (next === "system") localStorage.removeItem("theme");
      else localStorage.setItem("theme", next);
    } catch {
      // Storage can be blocked (e.g. private mode). The theme still applies for this visit.
    }
    apply(next);
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }

  return (
    <fieldset>
      <legend className="sr-only">Colour theme</legend>
      <div className="flex rounded-md border border-line p-0.5 text-sm">
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={theme === option.value}
            onClick={() => choose(option.value)}
            className="flex-1 rounded-[4px] px-2 py-1 text-muted aria-pressed:bg-canvas aria-pressed:font-medium aria-pressed:text-ink"
          >
            {option.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
