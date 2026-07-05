import { test, expect } from "@playwright/test";
import { mockApiHealthOk } from "../fixtures/mock-sse";

test.describe("UI-01 Page load", () => {
  test.beforeEach(async ({ page }) => {
    await mockApiHealthOk(page);
  });

  test("shows main workflow sections and backend health", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Critical Research Workflow" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Inputs" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Results" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "History" })).toBeVisible();
    await expect(page.getByText("Crew: idle")).toBeVisible();
    await expect(page.getByText(/Backend API: connected/i)).toBeVisible({ timeout: 10_000 });
  });
});
