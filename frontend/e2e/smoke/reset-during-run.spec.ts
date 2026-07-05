import { test, expect } from "@playwright/test";
import {
  buildInScopeSseBody,
  mockApiHealthOk,
  mockChatStreamDelayed,
} from "../fixtures/mock-sse";

test.describe("UI-07 Reset during run", () => {
  test.beforeEach(async ({ page }) => {
    await mockApiHealthOk(page);
    await mockChatStreamDelayed(page, buildInScopeSseBody(), 3_000);
    await page.goto("/");
  });

  test("abort in-flight stream and return to idle", async ({ page }) => {
    await page.getByLabel("Your question").fill("How do I submit an OCF-18?");
    await page.getByRole("button", { name: "Run" }).click();

    await expect(page.getByText("Crew: running")).toBeVisible();
    await page.getByRole("button", { name: "Reset" }).click();

    await expect(page.getByText("Crew: idle")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByLabel("Your question")).toBeEnabled();
  });
});
