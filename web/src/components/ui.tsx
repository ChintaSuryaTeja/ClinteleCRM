/** Small building blocks shared by every screen. */

import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

const PRIMARY =
  "inline-flex h-10 items-center justify-center rounded-md bg-accent px-4 font-medium text-on-accent hover:bg-accent-strong disabled:cursor-wait disabled:opacity-70";
const SECONDARY =
  "inline-flex h-10 items-center justify-center rounded-md border border-line bg-surface px-4 font-medium text-ink hover:bg-canvas disabled:cursor-wait disabled:opacity-70";
const DANGER =
  "inline-flex h-10 items-center justify-center rounded-md bg-danger px-4 font-medium text-surface hover:opacity-90 disabled:cursor-wait disabled:opacity-70";
const FIELD =
  "h-10 rounded-md border border-line bg-surface px-3 text-base text-ink placeholder:text-muted focus-visible:border-accent";

export function PageTitle({ children }: { children: ReactNode }) {
  return (
    <h1 className="text-[2rem] leading-tight font-semibold font-stretch-condensed tracking-tight">
      {children}
    </h1>
  );
}

export function Panel({ className = "", ...props }: ComponentProps<"section">) {
  return (
    <section className={`rounded-[10px] border border-line bg-surface ${className}`} {...props} />
  );
}

type TextFieldProps = ComponentProps<"input"> & { label: string; hint?: string };

export function TextField({ label, hint, id, ...props }: TextFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input id={id} aria-describedby={hintId} className={FIELD} {...props} />
      {hint && (
        <p id={hintId} className="text-sm text-muted">
          {hint}
        </p>
      )}
    </div>
  );
}

type Variant = { variant?: "primary" | "secondary" | "danger" };
const VARIANTS = { primary: PRIMARY, secondary: SECONDARY, danger: DANGER };

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ComponentProps<"button"> & Variant) {
  return <button className={`${VARIANTS[variant]} ${className}`} {...props} />;
}

export function ButtonLink({
  variant = "primary",
  className = "",
  ...props
}: ComponentProps<typeof Link> & Variant) {
  return <Link className={`${VARIANTS[variant]} ${className}`} {...props} />;
}

type SelectFieldProps = ComponentProps<"select"> & { label: string };

export function SelectField({ label, id, children, ...props }: SelectFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <select id={id} className={FIELD} {...props}>
        {children}
      </select>
    </div>
  );
}

/** A section heading inside a page. */
export function SectionTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-base font-semibold">{children}</h2>;
}

/** What a screen shows before there is any data: what's missing and what to do about it. */
export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Panel className="px-6 py-10 sm:px-10 sm:py-14">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="mt-2 max-w-[60ch] text-muted">{children}</div>
    </Panel>
  );
}

/** What a screen shows when loading failed, with a way to try again. */
export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Panel role="alert" className="px-6 py-10 sm:px-10">
      <h2 className="text-lg font-semibold">This page didn&apos;t load</h2>
      <p className="mt-2 max-w-[60ch] text-muted">{message}</p>
      <Button type="button" onClick={onRetry} className="mt-6">
        Try again
      </Button>
    </Panel>
  );
}

/** Grey placeholder blocks shown while a screen loads. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`rounded-md bg-line/60 motion-safe:animate-pulse ${className}`} />;
}

/** A problem the user can act on, announced to screen readers when it appears. */
export function ErrorNotice({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
      {children}
    </p>
  );
}
