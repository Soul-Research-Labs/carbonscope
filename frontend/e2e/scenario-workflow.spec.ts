import { test, expect } from "@playwright/test";

test.describe("Protected route workflow", () => {
  test("scenario route preserves intended destination in redirect", async ({
    page,
  }) => {
    await page.goto("/scenarios");
    await expect(page).toHaveURL(/\/login\?redirect=%2Fscenarios/);
  });

  test("scenario filter URL is preserved in redirect", async ({ page }) => {
    await page.goto("/scenarios?status=computed");
    await expect(page).toHaveURL(
      /\/login\?status=computed&redirect=%2Fscenarios/,
    );
  });

  test("dashboard route redirects unauthenticated user", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login\?redirect=%2Fdashboard/);
  });
});
