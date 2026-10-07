import path from "node:path";

import { expect, type Page } from "@playwright/test";

export const PASSWORD = "e2e-password-123";

/** A unique email per test run, so tests can run again against the same database. */
export function uniqueEmail(name: string): string {
  return `${name}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@e2e.example.com`;
}

/** Sign up a new organization through the form; ends on the dashboard. */
export async function signUp(page: Page, organization: string, email: string) {
  await page.goto("/signup");
  await page.fill("#organization_name", organization);
  await page.selectOption("#currency", "USD");
  await page.fill("#email", email);
  await page.fill("#password", PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/dashboard");
}

export async function logIn(page: Page, email: string) {
  await page.goto("/login");
  await page.fill("#email", email);
  await page.fill("#password", PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/dashboard");
}

// The template the Import page offers: 2 orders, 2 customers, $43.50 in total.
export const TEMPLATE = path.join(__dirname, "..", "..", "web", "public", "import-template.csv");

/** Upload the template on the Import page and wait for the worker to finish it. */
export async function importTemplate(page: Page) {
  await page.goto("/import");
  await page.setInputFiles("#file", TEMPLATE);
  await page.getByRole("button", { name: "Upload and import" }).click();
  const row = page.getByRole("row", { name: /import-template\.csv/ });
  // The page refreshes itself while the import runs in the background.
  await expect(row.getByText("Done")).toBeVisible({ timeout: 45_000 });
}
