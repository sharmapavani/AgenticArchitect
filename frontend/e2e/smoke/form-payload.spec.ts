import { test, expect } from "@playwright/test";
import {
  buildInScopeSseBody,
  captureChatStreamPayload,
  mockApiHealthOk,
} from "../fixtures/mock-sse";

test.describe("UI-05 / UI-06 Form payload", () => {
  test("sends French language and insurers portal_hint", async ({ page }) => {
    await mockApiHealthOk(page);
    const getPayload = await captureChatStreamPayload(page, buildInScopeSseBody());
    await page.goto("/");

    await page.getByLabel("Language").selectOption("fr");
    await page.getByLabel("Portal hint (optional)").selectOption("insurers");
    await page.getByLabel("Your question").fill("How do I review adjudication reason codes?");
    await page.getByRole("button", { name: "Run" }).click();

    await expect(page.getByText("Crew: done")).toBeVisible({ timeout: 15_000 });

    const payload = getPayload();
    expect(payload).not.toBeNull();
    expect(payload?.language).toBe("fr");
    expect(payload?.portal_hint).toBe("insurers");
    expect(payload?.message).toContain("adjudication reason codes");
  });
});
