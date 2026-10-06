import type { ReactNode } from "react";

import { Wordmark } from "@/components/Wordmark";

/** Frame for the login and signup pages: wordmark, one line on what the app does, the form. */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[26rem] flex-col px-4 py-10 sm:py-16">
      <Wordmark />
      <p className="mt-10 text-[2.5rem] leading-[1.05] font-semibold font-stretch-condensed tracking-tight sm:text-5xl">
        Know which customers to keep, grow and win back.
      </p>
      <div className="mt-10">{children}</div>
    </div>
  );
}
