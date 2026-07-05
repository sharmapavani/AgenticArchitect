import { test, expect } from "@playwright/test";
import { buildScopeRefusalSseBody, mockApiHealthOk, mockChatStream } from "../fixtures/mock-sse";

test.describe("UI-03 / E2E-01 Scope refusal", () => {
  test.beforeEach(async ({ page }) => {
    await mockApiHealthOk(page);
    await mockChatStream(page, buildScopeRefusalSseBody());
    await page.goto("/");
  });

  test("shows scope refusal in results and updates history", async ({ page }) => {
    await page.getByLabel("Your question").fill("What's the weather today?");
    await page.getByRole("button", { name: "Run" }).click();

    await expect(page.getByText("Crew: running")).toBeVisible();
    await expect(page.getByText("Crew: done")).toBeVisible({ timeout: 15_000 });

    await expect(
      page.getByText(/I can only assist with CAI and NYC auto insurance health claims topics/)
    ).toBeVisible();

    await expect(page.getByRole("list", { name: "Past research runs" }).getByRole("button")).toHaveCount(1);
  });
});
