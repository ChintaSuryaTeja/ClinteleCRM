import type { NextConfig } from "next";

// Where the FastAPI service is reachable from the Next.js server.
const apiUrl = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Production builds include a minimal server with only the packages it needs,
  // which keeps the production Docker image small (see web/Dockerfile).
  output: "standalone",
  // Don't announce which framework the site runs on.
  poweredByHeader: false,
  // The dev-only Next.js badge, moved away from the sidebar's account controls.
  devIndicators: { position: "bottom-right" },
  // The browser calls /api/... on this site and Next.js forwards the request
  // to FastAPI. To the browser everything is one site, so the login cookie
  // works without any cross-origin (CORS) setup.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/:path*` }];
  },
};

export default nextConfig;
