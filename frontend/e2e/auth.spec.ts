import { test, expect } from "@playwright/test";

test.describe("Login page", () => {
  test("renders login form with required fields", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByPlaceholder("simon@example.com")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Se connecter" })
    ).toBeVisible();
    await expect(page.getByText("Créer un compte")).toBeVisible();
  });
});

test.describe("Register page", () => {
  test("renders registration form with required fields", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByPlaceholder("Simon", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Créer mon compte" })
    ).toBeVisible();
    await expect(page.getByText("Se connecter")).toBeVisible();
  });
});
