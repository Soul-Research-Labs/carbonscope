import { test, expect } from "@playwright/test";

const PROTECTED_ROUTES = [
  "/marketplace",
  "/scenarios",
  "/settings",
  "/upload",
  "/dashboard",
  "/benchmarks",
  "/compliance",
  "/alerts",
  "/audit-logs",
  "/questionnaires",
  "/reviews",
  "/supply-chain",
  "/reports",
  "/pcaf",
  "/recommendations",
  "/billing",
];

for (const route of PROTECTED_ROUTES) {
  test(`${route} redirects unauthenticated users to login`, async ({
    page,
  }) => {
    await page.goto(route);
    await expect(page).toHaveURL(/login/, { timeout: 5000 });
  });
}
