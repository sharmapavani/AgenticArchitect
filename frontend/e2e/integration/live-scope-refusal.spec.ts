import { test, expect } from "@playwright/test";

/**
 * Live integration — requires FastAPI backend on :8000.
 * Skipped when backend is not reachable.
 */
test.describe("E2E-01 Live scope refusal @integration", () => {
  test.beforeEach(async ({ request }) => {
    try {
      const health = await request.get("http://127.0.0.1:8000/health", { timeout: 5_000 });
      if (!health.ok()) {
        test.skip(true, "Backend not running on :8000");
      }
    } catch {
      test.skip(true, "Backend not running on :8000");
    }
  });

  test("live backend returns scope refusal for weather query", async ({ page }) => {
    await page.goto("/");

    await page.getByLabel("Your question").fill("What's the weather today?");
    await page.getByRole("button", { name: "Run" }).click();

    await expect(page.getByText("Crew: running")).toBeVisible();
    await expect(page.getByText("Crew: done")).toBeVisible({ timeout: 30_000 });
    await expect(
      page.getByText(/I can only assist with CAI and NYC auto insurance health claims topics/i)
    ).toBeVisible();
  });
});
