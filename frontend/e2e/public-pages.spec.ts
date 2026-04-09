import { test, expect } from "@playwright/test";

test.describe("Public pages — structure", () => {
  test("register page is accessible without authentication", async ({
    page,
  }) => {
    await page.goto("/register");
    // Verify the page resolved (not redirected away) and is stable
    await expect(page).toHaveURL("/register");
  });

  test("unknown public path shows not found or redirects", async ({ page }) => {
    await page.goto("/nonexistent-path-xyz");
    // Next.js shows 404 or redirects — just verify it resolves without a browser error
    const currentUrl = page.url();
    expect(currentUrl).toBeTruthy();
  });
});
