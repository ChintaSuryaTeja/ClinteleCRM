import Link from "next/link";

export function Wordmark() {
  return (
    <Link
      href="/dashboard"
      className="text-xl font-semibold font-stretch-condensed tracking-tight text-ink"
    >
      Clientele
    </Link>
  );
}
