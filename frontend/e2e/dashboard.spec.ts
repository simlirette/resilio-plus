import { test, expect } from "@playwright/test";

test.describe("Protected routes — unauthenticated", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a public page first (needed to execute JS on the domain)
    await page.goto("/login");
    // Clear any existing auth token
    await page.evaluate(() => localStorage.clear());
  });

  test("/dashboard redirects to /login when not authenticated", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    await page.waitForURL("/login", { timeout: 5_000 });
    await expect(page).toHaveURL("/login");
  });

  test("/dashboard/calendar redirects to /login when not authenticated", async ({
    page,
  }) => {
    await page.goto("/dashboard/calendar");
    await page.waitForURL("/login", { timeout: 5_000 });
    await expect(page).toHaveURL("/login");
  });
});
