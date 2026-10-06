import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE } from "@/lib/session";

/**
 * Runs before every matched page request. Visitors without a login cookie are
 * sent to /login straight away. This is only a quick check: the API still
 * verifies the token on every request, which is the real protection.
 */
export function proxy(request: NextRequest) {
  if (!request.cookies.has(SESSION_COOKIE)) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Every page except the login/signup pages, API calls and static files.
  matcher: ["/((?!login|signup|api|_next/static|_next/image|favicon.ico).*)"],
};
