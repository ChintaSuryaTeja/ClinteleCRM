import { defineConfig, devices } from "@playwright/test";

/**
 * Browser tests for the running app. Start the production stack first
 * (deploy/docker-compose.prod.yml), then run `npx playwright test`.
 *
 * BASE_URL is where the app is: https://localhost by default.
 */
export default defineConfig({
  testDir: "./tests",
  // Each test signs up its own organizations, so tests don't depend on each other.
  fullyParallel: true,
  workers: 2,
  retries: process.env.CI ? 1 : 0,
  forbidOnly: !!process.env.CI,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.BASE_URL ?? "https://localhost",
    // Locally and in CI the certificate is self-signed.
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
