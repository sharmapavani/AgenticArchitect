import { test, expect } from "@playwright/test";
import { buildInScopeSseBody, mockApiHealthOk, mockChatStream } from "../fixtures/mock-sse";

test.describe("UI-09 History select", () => {
  test.beforeEach(async ({ page }) => {
    await mockApiHealthOk(page);
    await mockChatStream(page, buildInScopeSseBody());
    await page.goto("/");
  });

  test("hydrates read-only results from history entry", async ({ page }) => {
    await page.getByLabel("Your question").fill("How do I reactivate a user?");
    await page.getByRole("button", { name: "Run" }).click();
    await expect(page.getByText("Crew: done")).toBeVisible({ timeout: 15_000 });

    const historyButton = page.getByRole("list", { name: "Past research runs" }).getByRole("button").first();
    await expect(historyButton).toBeVisible();

    await page.getByLabel("Your question").fill("Different question for new run");
    await historyButton.click();

    await expect(page.getByText(/reactivate a deactivated user/i)).toBeVisible();
    await expect(page.getByRole("button", { name: "Reset" })).toBeDisabled();
  });
});
