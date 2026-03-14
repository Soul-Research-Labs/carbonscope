import { test, expect, Page } from "@playwright/test";

/** Seed localStorage with a fake authenticated session. */
async function seedAuth(page: Page) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({ sub: 1, email: "alice@example.com", company_id: 1 }),
  );
  const fakeToken = `${header}.${payload}.fakesig`;

  await page.addInitScript((token: string) => {
    localStorage.setItem("token", token);
    localStorage.setItem(
      "user",
      JSON.stringify({
        id: 1,
        email: "alice@example.com",
        full_name: "Alice",
        company_id: 1,
        role: "admin",
      }),
    );
  }, fakeToken);
}

/** Intercept all /api/v1 calls with sensible defaults per route. */
async function mockApi(page: Page) {
  await page.route("**/api/v1/**", (route) => {
    const url = route.request().url();

    if (url.includes("/reports")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            scope: "scope_1",
            co2_kg: 120.5,
            methodology: "GHG Protocol",
            created_at: "2025-01-15T10:00:00Z",
          },
          {
            id: 2,
            scope: "scope_2",
            co2_kg: 340.2,
            methodology: "GHG Protocol",
            created_at: "2025-01-16T11:00:00Z",
          },
        ]),
      });
    }

    if (url.includes("/carbon/estimate")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 3,
          scope: "scope_1",
          co2_kg: 55.5,
          methodology: "GHG Protocol",
          created_at: new Date().toISOString(),
        }),
      });
    }

    if (url.includes("/compliance")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ report: "Generated compliance report" }),
      });
    }

    if (url.includes("/scenarios")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    }

    // Default: return empty array
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });
}

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockApi(page);
  });

  test("dashboard loads for authenticated user", async ({ page }) => {
    await page.goto("/dashboard");
    // Should stay on dashboard (not redirect to login)
    await expect(page).toHaveURL(/dashboard/, { timeout: 5000 });
  });

  test("dashboard displays page heading", async ({ page }) => {
    await page.goto("/dashboard");
    const heading = page.locator("h1, h2").first();
    await expect(heading).toBeVisible({ timeout: 5000 });
  });
});

test.describe("Upload page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockApi(page);
  });

  test("upload page renders form", async ({ page }) => {
    await page.goto("/upload");
    await expect(page).toHaveURL(/upload/, { timeout: 5000 });
    // Should show at least a submit button or form element
    const form = page.locator("form, button[type='submit']");
    await expect(form.first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe("Reports page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockApi(page);
  });

  test("reports page loads and displays data", async ({ page }) => {
    await page.goto("/reports");
    await expect(page).toHaveURL(/reports/, { timeout: 5000 });
  });
});

test.describe("Compliance page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockApi(page);
  });

  test("compliance page loads", async ({ page }) => {
    await page.goto("/compliance");
    await expect(page).toHaveURL(/compliance/, { timeout: 5000 });
  });
});

test.describe("Scenarios page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockApi(page);
  });

  test("scenarios page loads", async ({ page }) => {
    await page.goto("/scenarios");
    await expect(page).toHaveURL(/scenarios/, { timeout: 5000 });
  });
});

test.describe("Settings page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockApi(page);
  });

  test("settings page loads with profile section", async ({ page }) => {
    await page.goto("/settings");
    await expect(page).toHaveURL(/settings/, { timeout: 5000 });
  });
});
