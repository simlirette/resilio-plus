import { test, expect } from "@playwright/test";

test.describe("Protected routes — unauthenticated", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a public page first (needed to execute JS on the domain)
    await page.goto("/login");
    // Clear any existing auth token
    await page.evaluate(() => localStorage.clear());
  });

  test("/dashboard/chat redirects to /login when not authenticated", async ({
    page,
  }) => {
    await page.goto("/dashboard/chat");
    await page.waitForURL("/login", { timeout: 5_000 });
    await expect(page).toHaveURL("/login");
  });

  test("/dashboard/weekly-review redirects to /login when not authenticated", async ({
    page,
  }) => {
    await page.goto("/dashboard/weekly-review");
    await page.waitForURL("/login", { timeout: 5_000 });
    await expect(page).toHaveURL("/login");
  });

  test("/dashboard/plan/running redirects to /login when not authenticated", async ({
    page,
  }) => {
    await page.goto("/dashboard/plan/running");
    await page.waitForURL("/login", { timeout: 5_000 });
    await expect(page).toHaveURL("/login");
  });

  test("/dashboard/plan/lifting redirects to /login when not authenticated", async ({
    page,
  }) => {
    await page.goto("/dashboard/plan/lifting");
    await page.waitForURL("/login", { timeout: 5_000 });
    await expect(page).toHaveURL("/login");
  });
});
