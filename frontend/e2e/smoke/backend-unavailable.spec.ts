import { test, expect } from "@playwright/test";
import { mockApiHealthUnavailable } from "../fixtures/mock-sse";

test.describe("UI-10 Backend unavailable", () => {
  test("shows unavailable health status", async ({ page }) => {
    await mockApiHealthUnavailable(page);
    await page.goto("/");

    await expect(page.getByText(/Backend API: unavailable/i)).toBeVisible({
      timeout: 10_000,
    });
  });
});
