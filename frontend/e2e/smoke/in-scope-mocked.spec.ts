import { test, expect } from "@playwright/test";
import { buildInScopeSseBody, mockApiHealthOk, mockChatStream } from "../fixtures/mock-sse";

test.describe("UI-04 In-scope run (mocked SSE)", () => {
  test.beforeEach(async ({ page }) => {
    await mockApiHealthOk(page);
    await mockChatStream(page, buildInScopeSseBody());
    await page.goto("/");
  });

  test("shows agent progress, answer, citations, and workflow", async ({ page }) => {
    await page.getByLabel("Your question").fill("How do I reactivate a deactivated user?");
    await page.getByRole("button", { name: "Run" }).click();

    await expect(page.getByText("Crew: running")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Agent progress" })).toBeVisible();
    await expect(page.getByText("Crew: done")).toBeVisible({ timeout: 15_000 });

    const resultsSection = page.locator("section").filter({ has: page.getByRole("heading", { name: "Results" }) });
    await expect(resultsSection.getByText(/To reactivate a deactivated user/i)).toBeVisible();
    await expect(resultsSection.getByRole("heading", { name: "Citations" })).toBeVisible();
    await expect(resultsSection.getByRole("link", { name: /Managing-Users\.pdf/i })).toBeVisible();
    await expect(resultsSection.getByText("User reactivation")).toBeVisible();
  });
});
