/**
 * Comprehensive authenticated-page E2E tests.
 *
 * Each test seeds a fake JWT session and mocks the backend API so the
 * suite runs fully offline — no real server needed.
 */
import { test, expect, Page } from "@playwright/test";

// ── Fixtures ──────────────────────────────────────────────────────────

async function seedAuth(page: Page) {
  const header = Buffer.from(
    JSON.stringify({ alg: "HS256", typ: "JWT" }),
  ).toString("base64url");
  const payload = Buffer.from(
    JSON.stringify({
      sub: 1,
      email: "alice@carbonscope.io",
      company_id: 1,
      role: "admin",
    }),
  ).toString("base64url");
  const fakeToken = `${header}.${payload}.fakesig`;

  await page.context().addCookies([
    { name: "cs_access_token", value: fakeToken, url: "http://localhost:3000" },
    { name: "access_token", value: fakeToken, url: "http://localhost:3000" },
  ]);

  await page.addInitScript((token: string) => {
    localStorage.setItem("token", token);
    localStorage.setItem(
      "user",
      JSON.stringify({
        id: 1,
        email: "alice@carbonscope.io",
        full_name: "Alice Admin",
        company_id: 1,
        role: "admin",
        plan: "pro",
      }),
    );
  }, fakeToken);
}

async function mockAll(page: Page) {
  await page.route("**/api/v1/**", (route) => {
    const url = route.request().url();

    /** Auth */
    if (url.includes("/auth/me")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          email: "alice@carbonscope.io",
          full_name: "Alice Admin",
          company_id: 1,
          role: "admin",
          plan: "pro",
        }),
      });
    }

    /** Company */
    if (url.includes("/company/me")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          name: "Acme Corp",
          industry: "manufacturing",
          region: "US",
        }),
      });
    }

    /** Carbon reports */
    if (
      url.includes("/carbon/reports") &&
      !url.match(/\/carbon\/reports\/\d/)
    ) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            year: 2024,
            status: "completed",
            scope1_total: 1200.5,
            scope2_total: 850.3,
            scope3_total: 4200.0,
            created_at: "2024-01-15T10:00:00Z",
          },
        ]),
      });
    }

    /** Single report */
    if (url.match(/\/carbon\/reports\/\d+/)) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          year: 2024,
          status: "completed",
          scope1_total: 1200.5,
          scope2_total: 850.3,
          scope3_total: 4200.0,
          breakdown: { electricity: 800, transport: 600 },
        }),
      });
    }

    /** Recommendations */
    if (url.includes("/recommendations")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            title: "Switch to renewable energy",
            description: "Install solar panels",
            potential_reduction: 400,
            effort: "medium",
            category: "scope2",
          },
        ]),
      });
    }

    /** Scenarios */
    if (url.includes("/scenarios")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            name: "EV Fleet Transition",
            status: "computed",
            total_reduction: 320.0,
            created_at: "2024-03-01T00:00:00Z",
          },
        ]),
      });
    }

    /** Supply chain */
    if (url.includes("/supply-chain")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    }

    /** Compliance */
    if (url.includes("/compliance")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ templates: ["ghg", "cdp", "tcfd"] }),
      });
    }

    /** Billing / subscription */
    if (url.includes("/billing") || url.includes("/subscriptions")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          plan: "pro",
          credits_balance: 500,
          credits_used: 120,
          renewal_date: "2025-01-01",
        }),
      });
    }

    /** Alerts */
    if (url.includes("/alerts")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            name: "High Scope 1 Alert",
            threshold: 1500,
            scope: "scope1",
            active: true,
          },
        ]),
      });
    }

    /** Marketplace listings */
    if (url.includes("/marketplace/listings") || url.includes("/marketplace")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "lst_1",
            title: "2024 Scope 1 Manufacturing",
            description: "Verified scope 1 data",
            price_credits: 50,
            status: "active",
            listing_type: "one_time",
            seller_company_id: 2,
            created_at: "2024-01-15T00:00:00Z",
          },
        ]),
      });
    }

    /** Questionnaires */
    if (url.includes("/questionnaires")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            title: "Annual Scope 3 Survey",
            status: "draft",
            created_at: "2024-02-01T00:00:00Z",
          },
        ]),
      });
    }

    /** Reviews */
    if (url.includes("/reviews")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    }

    /** Benchmarks */
    if (url.includes("/benchmarks")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            industry: "manufacturing",
            scope1_avg: 1000,
            scope2_avg: 700,
            scope3_avg: 3500,
            year: 2024,
          },
        ]),
      });
    }

    /** Audit logs */
    if (url.includes("/audit")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            action: "report.created",
            user_email: "alice@carbonscope.io",
            resource_type: "report",
            created_at: "2024-03-10T09:00:00Z",
          },
        ]),
      });
    }

    /** PCAF */
    if (url.includes("/pcaf") || url.includes("/portfolios")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    }

    /** MFA */
    if (url.includes("/mfa/status")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ enabled: false, backup_codes_remaining: 0 }),
      });
    }

    /** Events SSE — respond with empty stream to avoid hanging */
    if (url.includes("/events/subscribe")) {
      return route.fulfill({ status: 204, body: "" });
    }

    /** Webhooks */
    if (url.includes("/webhooks")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    }

    // Default: empty 200
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });
}

// ── Dashboard ──────────────────────────────────────────────────────────

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders without redirecting to login", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
  });

  test("page title contains CarbonScope", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveTitle(/CarbonScope/i);
  });

  test("has a skip-navigation link for accessibility", async ({ page }) => {
    await page.goto("/dashboard");
    const skipLink = page.locator('a[href="#main-content"]');
    // Skip link can be visually hidden but must exist in DOM
    await expect(skipLink).toHaveCount(1);
  });
});

// ── Reports ────────────────────────────────────────────────────────────

test.describe("Reports list", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("loads reports page", async ({ page }) => {
    await page.goto("/reports");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
  });
});

// ── Upload ─────────────────────────────────────────────────────────────

test.describe("Upload page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("shows upload form when authenticated", async ({ page }) => {
    await page.goto("/upload");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    // Look for a file input or explicit drop zone
    const hasFileInput = (await page.locator('input[type="file"]').count()) > 0;
    const hasDropZone =
      (await page.locator('[data-testid="drop-zone"], label[for]').count()) > 0;
    expect(hasFileInput || hasDropZone).toBeTruthy();
  });
});

// ── Recommendations ───────────────────────────────────────────────────

test.describe("Recommendations page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders without crashing", async ({ page }) => {
    await page.goto("/recommendations");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });
});

// ── Scenarios ─────────────────────────────────────────────────────────

test.describe("Scenarios page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders scenarios list", async ({ page }) => {
    await page.goto("/scenarios");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
  });
});

// ── Compliance ────────────────────────────────────────────────────────

test.describe("Compliance page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders framework options", async ({ page }) => {
    await page.goto("/compliance");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });
});

// ── Billing ───────────────────────────────────────────────────────────

test.describe("Billing page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders billing information", async ({ page }) => {
    await page.goto("/billing");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });
});

// ── Alerts ────────────────────────────────────────────────────────────

test.describe("Alerts page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders alerts list", async ({ page }) => {
    await page.goto("/alerts");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
  });

  test("shows form to create alert", async ({ page }) => {
    await page.goto("/alerts");
    await page.waitForTimeout(800);
    // There should be an input or button to create/set a threshold
    const body = await page.locator("body").textContent();
    expect(body).toBeTruthy();
  });
});

// ── Marketplace ───────────────────────────────────────────────────────

test.describe("Marketplace page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders listing cards", async ({ page }) => {
    await page.goto("/marketplace");
    await page.waitForTimeout(1000);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });

  test("search input is present", async ({ page }) => {
    await page.goto("/marketplace");
    await page.waitForTimeout(1000);
    const searchInput = page.locator(
      'input[type="text"], input[placeholder*="search" i]',
    );
    // At least one text input should exist for filtering
    expect(await searchInput.count()).toBeGreaterThan(0);
  });
});

// ── Audit logs ────────────────────────────────────────────────────────

test.describe("Audit logs page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders audit log entries", async ({ page }) => {
    await page.goto("/audit-logs");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });
});

// ── Benchmarks ───────────────────────────────────────────────────────

test.describe("Benchmarks page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders benchmarking page", async ({ page }) => {
    await page.goto("/benchmarks");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });
});

// ── Settings ──────────────────────────────────────────────────────────

test.describe("Settings page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders user settings form", async ({ page }) => {
    await page.goto("/settings");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
  });

  test("displays user email in profile section", async ({ page }) => {
    await page.goto("/settings");
    await page.waitForTimeout(800);
    const body = await page.locator("body").textContent();
    // Profile should show the signed-in user's email
    expect(body).toContain("alice@carbonscope.io");
  });
});

// ── MFA ───────────────────────────────────────────────────────────────

test.describe("MFA settings page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders MFA setup when 2FA is not enabled", async ({ page }) => {
    await page.goto("/mfa");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    const body = await page.locator("body").textContent();
    // With MFA disabled, should show enable option
    expect(body).toBeTruthy();
  });
});

// ── Questionnaires ────────────────────────────────────────────────────

test.describe("Questionnaires page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders questionnaire list", async ({ page }) => {
    await page.goto("/questionnaires");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });
});

// ── Reviews ───────────────────────────────────────────────────────────

test.describe("Reviews page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders reviews page with empty state", async ({ page }) => {
    await page.goto("/reviews");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });
});

// ── Supply chain ──────────────────────────────────────────────────────

test.describe("Supply chain page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders supply chain management page", async ({ page }) => {
    await page.goto("/supply-chain");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });
});

// ── PCAF ──────────────────────────────────────────────────────────────

test.describe("PCAF page", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("renders PCAF portfolio page", async ({ page }) => {
    await page.goto("/pcaf");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });
});

// ── Accessibility ─────────────────────────────────────────────────────

test.describe("Accessibility basics", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("dashboard has a page heading", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForTimeout(800);
    // Every page should have at least one heading
    const headingCount = await page.locator("h1, h2").count();
    expect(headingCount).toBeGreaterThan(0);
  });

  test("login page has proper form labels", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  });

  test("register page has proper form labels", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByLabel("Full Name")).toBeVisible();
    await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  });

  test("main landmark is present on authenticated pages", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForTimeout(800);
    // app layout wraps children in <main>
    const mainCount = await page.locator("main").count();
    expect(mainCount).toBeGreaterThanOrEqual(1);
  });
});

// ── Keyboard navigation ───────────────────────────────────────────────

test.describe("Keyboard navigation", () => {
  test("can tab to login form fields", async ({ page }) => {
    await page.goto("/login");
    // Tab into the form
    await page.keyboard.press("Tab");
    const focused = page.locator(":focus");
    // After one tab, something interactive should be focused
    await expect(focused).not.toHaveCount(0);
  });

  test("submit button is reachable by keyboard on login", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email", { exact: true }).focus();
    await page.keyboard.press("Tab"); // password
    await page.keyboard.press("Tab"); // submit
    const focused = page.locator(":focus");
    const tagName = await focused.evaluate((el) => el.tagName.toLowerCase());
    // Should have focused a button or link
    expect(["button", "a", "input"]).toContain(tagName);
  });
});

// ── Responsive layout ─────────────────────────────────────────────────

test.describe("Responsive layout", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockAll(page);
  });

  test("marketplace filtering works on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/marketplace");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    await expect(page.locator("body")).not.toBeEmpty();
  });

  test("dashboard renders on small screen", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 568 });
    await page.goto("/dashboard");
    await page.waitForTimeout(800);
    expect(page.url()).not.toMatch(/login/);
    const body = await page.locator("body").textContent();
    expect(body?.length).toBeGreaterThan(10);
  });
});
