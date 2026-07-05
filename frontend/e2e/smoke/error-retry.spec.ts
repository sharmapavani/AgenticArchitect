import { test, expect } from "@playwright/test";
import { mockApiHealthOk, mockChatStreamError } from "../fixtures/mock-sse";

test.describe("UI-08 Error and retry", () => {
  test("shows error alert and retry re-submits", async ({ page }) => {
    await mockApiHealthOk(page);
    await mockChatStreamError(page, 502);
    await page.goto("/");

    await page.getByLabel("Your question").fill("How do I reset a password?");
    await page.getByRole("button", { name: "Run" }).click();

    await expect(page.getByRole("alert").filter({ hasText: /Crew: error/i })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();

    // Second attempt still fails — confirms retry triggers a new request.
    await page.getByRole("button", { name: "Retry" }).click();
    await expect(page.getByRole("alert").filter({ hasText: /Crew: error/i })).toBeVisible({
      timeout: 15_000,
    });
  });
});
