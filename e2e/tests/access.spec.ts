import { expect, test } from "@playwright/test";

import { PASSWORD, importTemplate, logIn, signUp, uniqueEmail } from "./helpers";

test("a viewer can read data but not import it", async ({ page, browser }) => {
  await signUp(page, "E2E Roles", uniqueEmail("admin"));
  // The admin adds a viewer. page.request shares the admin's login cookie.
  const viewerEmail = uniqueEmail("viewer");
  const response = await page.request.post("/api/users", {
    data: { email: viewerEmail, password: PASSWORD, role: "viewer" },
  });
  expect(response.status()).toBe(201);

  const viewerContext = await browser.newContext();
  const viewer = await viewerContext.newPage();
  await logIn(viewer, viewerEmail);

  const nav = viewer.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link", { name: "Customers" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Import" })).toHaveCount(0);

  await viewer.goto("/import");
  await expect(viewer.getByText("Only admins can import data")).toBeVisible();
  await viewerContext.close();
});

test("one organization can't open another organization's customer", async ({ page, browser }) => {
  await signUp(page, "E2E Owner", uniqueEmail("owner"));
  await importTemplate(page);
  await page.goto("/customers");
  const href = await page.getByRole("link", { name: "Ada Lovelace" }).getAttribute("href");
  expect(href).toMatch(/^\/customers\/\d+$/);

  const otherContext = await browser.newContext();
  const other = await otherContext.newPage();
  await signUp(other, "E2E Other", uniqueEmail("other"));
  await other.goto(href!);

  await expect(other.getByRole("heading", { name: "Customer not found" })).toBeVisible();
  await expect(other.getByText("Ada Lovelace")).toHaveCount(0);
  await otherContext.close();
});
