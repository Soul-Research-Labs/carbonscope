import { test, expect } from "@playwright/test";

test.describe("Auth workflow", () => {
  test("login page exposes recovery and registration links", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("link", { name: "Forgot password?" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Register" })).toBeVisible();
  });

  test("register page renders required account fields", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByLabel("Full Name")).toBeVisible();
    await expect(page.getByLabel("Company Name")).toBeVisible();
    await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Confirm Password", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Create Account" })).toBeVisible();
    await expect(page).toHaveURL(/register/);
  });

  test("login submit keeps user on login when credentials are invalid", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email", { exact: true }).fill("invalid@example.com");
    await page.getByLabel("Password", { exact: true }).fill("wrongpass");
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page).toHaveURL(/login/);
  });
});
