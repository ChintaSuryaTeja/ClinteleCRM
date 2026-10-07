import { expect, test } from "@playwright/test";

import { importTemplate, signUp, uniqueEmail } from "./helpers";

test("sign up, import data, and see it on every screen", async ({ page }) => {
  await signUp(page, "E2E Shop", uniqueEmail("admin"));

  // A new organization starts empty.
  await expect(page.getByText("No sales data yet")).toBeVisible();

  // The upload goes through Nginx to the API; the worker imports it.
  await importTemplate(page);

  // Dashboard: US$43.50 from 2 orders by 2 customers (amounts are formatted
  // in British English, which writes US dollars as "US$").
  await page.goto("/dashboard");
  await expect(page.getByText("US$44", { exact: true })).toBeVisible();
  await expect(page.getByRole("definition").filter({ hasText: /^2$/ })).toHaveCount(2);
  await expect(page.getByRole("heading", { name: "Top customers" })).toBeVisible();

  // Customers list and a customer's page.
  await page.goto("/customers");
  await page.getByRole("link", { name: "Ada Lovelace" }).click();
  await expect(page.getByRole("heading", { name: "Ada Lovelace" })).toBeVisible();
  await expect(page.getByText("US$31.00").first()).toBeVisible();

  // The analytics screens render with this data.
  await page.goto("/segments");
  await expect(page.getByRole("heading", { name: "Who your customers are" })).toBeVisible();
  await page.goto("/retention");
  await expect(page.getByText("Months after the first order")).toBeVisible();
  await page.goto("/churn");
  await expect(page.getByRole("heading", { name: "Churn", exact: true })).toBeVisible();
});

test("the Ask screen explains when no AI key is set", async ({ page }) => {
  await signUp(page, "E2E Ask", uniqueEmail("ask"));

  await page.goto("/ask");
  await page.getByRole("button", { name: "Revenue by month" }).click();

  await expect(page.getByText("Questions aren't set up yet")).toBeVisible();
});

test("logged-out visitors are sent to the login page", async ({ page }) => {
  await page.goto("/customers");
  await expect(page).toHaveURL(/\/login$/);
});
