import type { Metadata } from "next";
import type { ReactNode } from "react";
import { IBM_Plex_Sans } from "next/font/google";

import "./globals.css";

// One variable font file covers every weight and the condensed widths used for titles.
const plex = IBM_Plex_Sans({
  variable: "--font-plex",
  subsets: ["latin"],
  axes: ["wdth"],
});

export const metadata: Metadata = {
  title: { default: "Clientele", template: "%s – Clientele" },
  description: "See which customers to keep, grow and win back.",
};

// Runs before the page paints, so a dark-mode user never sees a white flash.
const themeScript = `(function () {
  try {
    var saved = localStorage.getItem("theme");
    var dark = saved === "dark" || (saved !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  } catch (e) {}
})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // The theme script changes data-theme before React loads, which is expected.
    <html lang="en" className={`${plex.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full font-sans">{children}</body>
    </html>
  );
}
