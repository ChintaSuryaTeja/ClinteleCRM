/**
 * Table building blocks. Numbers are right-aligned so their digits line up;
 * text is left-aligned. Wide tables scroll sideways inside their own box on
 * small screens instead of stretching the page.
 */

import type { ComponentProps, ReactNode } from "react";

export function Table({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="overflow-x-auto">
      <table aria-label={label} className="w-full border-collapse text-sm">
        {children}
      </table>
    </div>
  );
}

type CellProps = { numeric?: boolean } & ComponentProps<"td">;

export function Th({ numeric, className = "", ...props }: CellProps & ComponentProps<"th">) {
  return (
    <th
      scope="col"
      className={`border-b border-line px-3 py-2 font-medium whitespace-nowrap text-muted first:pl-0 last:pr-0 ${
        numeric ? "text-right" : "text-left"
      } ${className}`}
      {...props}
    />
  );
}

export function Td({ numeric, className = "", ...props }: CellProps) {
  return (
    <td
      className={`border-b border-line px-3 py-2.5 first:pl-0 last:pr-0 ${
        numeric ? "text-right whitespace-nowrap" : ""
      } ${className}`}
      {...props}
    />
  );
}
