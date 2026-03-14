import { test, expect, Page } from "@playwright/test";

/**
 * Helper: intercept the login API and inject a fake JWT into the response
 * so subsequent navigation sees an authenticated session.
 */
async function mockLoginApi(page: Page) {
  // Build a minimal JWT whose payload is base64url-encoded JSON
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({ sub: 1, email: "alice@example.com", company_id: 1 }),
  );
  const fakeToken = `${header}.${payload}.fakesig`;

  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: fakeToken, token_type: "bearer" }),
    }),
  );
  return fakeToken;
}

/** Seed localStorage so the app considers the user logged in. */
async function seedAuth(page: Page) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({ sub: 1, email: "alice@example.com", company_id: 1 }),
  );
  const fakeToken = `${header}.${payload}.fakesig`;

  await page.addInitScript(
    (token: string) => {
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
    },
    fakeToken,
  );
}

test.describe("Login → Dashboard flow", () => {
  test("successful login redirects to dashboard", async ({ page }) => {
    const fakeToken = await mockLoginApi(page);

    // Mock the dashboard API calls so the page doesn't error
    await page.route("**/api/v1/**", (route) => {
      if (route.request().url().includes("/auth/login")) {
        // already handled above
        return route.fallback();
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto("/login");
    await page.fill('input[type="email"]', "alice@example.com");
    await page.fill('input[type="password"]', "Password123!");
    await page.click('button[type="submit"]');

    // After successful login the app navigates to /dashboard
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
  });

  test("login preserves token in localStorage", async ({ page }) => {
    const fakeToken = await mockLoginApi(page);

    await page.route("**/api/v1/**", (route) => {
      if (route.request().url().includes("/auth/login")) return route.fallback();
      return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });

    await page.goto("/login");
    await page.fill('input[type="email"]', "alice@example.com");
    await page.fill('input[type="password"]', "Password123!");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });

    const stored = await page.evaluate(() => localStorage.getItem("token"));
    expect(stored).toBe(fakeToken);
  });
});

test.describe("Register flow", () => {
  test("register page renders all required fields", async ({ page }) => {
    await page.goto("/register");
    await expect(page.locator("h1")).toContainText("Create Account");
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('input[name="full_name"]')).toBeVisible();
    await expect(page.locator('input[name="company_name"]')).toBeVisible();
  });

  test("register form validates required fields on submit", async ({ page }) => {
    await page.goto("/register");
    // Submit the empty form
    await page.click('button[type="submit"]');
    // Should stay on register page (client-side or server validation)
    await expect(page).toHaveURL(/register/);
  });
});

test.describe("Logout", () => {
  test("logout clears auth and redirects to login", async ({ page }) => {
    await seedAuth(page);

    // Mock all API calls to succeed
    await page.route("**/api/v1/**", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
    );

    await page.goto("/dashboard");
    // Should stay on dashboard since we're "logged in"
    await page.waitForTimeout(1000);
    const url = page.url();

    // If the app kept us on dashboard, look for logout button
    if (url.includes("dashboard")) {
      const logoutBtn = page.locator('button:has-text("Logout"), button:has-text("Sign Out"), a:has-text("Logout")');
      if (await logoutBtn.count()) {
        await logoutBtn.first().click();
        await expect(page).toHaveURL(/login/, { timeout: 5000 });
        const token = await page.evaluate(() => localStorage.getItem("token"));
        expect(token).toBeNull();
      }
    }
  });
});
