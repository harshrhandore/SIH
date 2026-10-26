import { test, expect } from "@playwright/test";
import { login, manifest } from "./helpers";

test("assigned officer sees a verified timeline from the real chain", async ({ page }) => {
  await login(page, "officer@example.test");
  const path = "/students/" + manifest.showcase_student_id + "/timeline";
  const response = await page.request.get("/api/backend" + path + "?page_size=25");
  expect(response.ok()).toBeTruthy();
  const timeline = await response.json();
  expect(timeline.verified).toBe(true);
  expect(timeline.checked_head_seq).toBeGreaterThan(0);
  expect(timeline.items.length).toBeGreaterThan(0);
  expect(timeline.items.every((event: { row_hash: string; hash_verified: boolean }) =>
    event.hash_verified && /^[0-9a-f]{64}$/.test(event.row_hash),
  )).toBe(true);

  await page.goto(path);
  await expect(page.getByRole("heading", { name: "Audit timeline", exact: true })).toBeVisible();
  await expect(page.getByText("Full chain verified", { exact: false })).toBeVisible();
  await expect(page.locator(".timeline article")).toHaveCount(timeline.items.length);
  await page.getByRole("combobox", { name: "Events per page", exact: true }).selectOption("50");
  await expect(page.getByRole("combobox", { name: "Events per page", exact: true })).toHaveValue("50");
  await expect(page.getByText("Full chain verified", { exact: false })).toBeVisible();
  await page.getByText("Stored row hash", { exact: true }).first().click();
  await expect(page.locator(".timeline code").first()).toHaveText(timeline.items[0].row_hash);
  await page.getByRole("button", { name: "Verify chain", exact: true }).click();
  await expect(page.getByText("Full chain verified", { exact: false })).toBeVisible();
});
