import { test, expect } from "@playwright/test";
import { mockApiHealthOk } from "../fixtures/mock-sse";

test.describe("UI-02 Form validation", () => {
  test.beforeEach(async ({ page }) => {
    await mockApiHealthOk(page);
    await page.goto("/");
  });

  test("blocks empty message submit", async ({ page }) => {
    await page.getByRole("button", { name: "Run" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Please enter your CAI question." })).toBeVisible();
    await expect(page.getByText("Crew: idle")).toBeVisible();
  });
});
