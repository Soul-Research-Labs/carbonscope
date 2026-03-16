import { test, expect } from "@playwright/test";

test.describe("Redirect workflow", () => {
  test("upload route redirects to login with redirect parameter", async ({
    page,
  }) => {
    await page.goto("/upload");
    await expect(page).toHaveURL(/\/login\?redirect=%2Fupload/);
  });

  test("reports route redirects to login with redirect parameter", async ({
    page,
  }) => {
    await page.goto("/reports");
    await expect(page).toHaveURL(/\/login\?redirect=%2Freports/);
  });

  test("login page can navigate to register", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("link", { name: "Register" }).click();
    await expect(page).toHaveURL(/register/);
    await expect(
      page.getByRole("heading", { name: /CarbonScope/i }),
    ).toBeVisible();
  });
});
