import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { login, manifest } from "./helpers";

test("shared layout persists and palette supports keyboard navigation", async ({
  page,
}) => {
  await login(page, "operator.a@example.test");
  const sidebar = await page.locator("aside.sidebar").elementHandle();
  await page
    .getByRole("navigation", { name: "Workspace navigation" })
    .getByRole("link", { name: "Student search" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Student search", exact: true }),
  ).toBeVisible();
  expect(
    await sidebar!.evaluate(
      (node) => node === document.querySelector("aside.sidebar"),
    ),
  ).toBe(true);
  await page.keyboard.press("Control+k");
  const dialog = page.getByRole("dialog", { name: "Search workspace" });
  await expect(dialog).toBeVisible();
  await page.getByLabel("Find a page or student").fill("Riya Sharma");
  await expect(dialog.getByRole("link", { name: /Riya Sharma/ })).toBeVisible();
  await page.keyboard.press("ArrowDown");
  await expect(dialog.getByRole("link", { name: /Riya Sharma/ })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(
    new RegExp("/students/" + manifest.showcase_student_id + "$"),
  );
  await expect(
    page.getByRole("heading", { name: "Riya Sharma", exact: true }),
  ).toBeVisible();
  const open = page.getByRole("button", {
    name: "Search workspace (Ctrl+K)",
    exact: true,
  });
  await open.click();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(open).toBeFocused();
  await page.setViewportSize({ width: 375, height: 812 });
  const toggle = page.getByRole("button", {
    name: "Toggle navigation",
    exact: true,
  });
  await toggle.click();
  const drawer = page.getByRole("dialog", {
    name: "Workspace navigation",
    exact: true,
  });
  await expect(drawer).toBeVisible();
  await expect(
    drawer.getByRole("button", { name: "Close navigation" }),
  ).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(drawer.getByRole("link").last()).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    drawer.getByRole("button", { name: "Close navigation" }),
  ).toBeFocused();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
  await expect(toggle).toBeFocused();
});

test("sign out clears authentication cookies and leaves workspace", async ({
  page,
  context,
}) => {
  await login(page, "officer@example.test");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  const cookies = await context.cookies();
  expect(
    cookies.filter((cookie) =>
      ["shiksham_access", "shiksham_refresh", "shiksham_csrf"].includes(
        cookie.name,
      ),
    ),
  ).toHaveLength(0);
  await expect(page.locator("aside.sidebar")).toHaveCount(0);
});

test("unknown URLs return 404 instead of demo controls", async ({ page }) => {
  const response = await page.goto("/unknown-workspace-page");
  expect(response?.status()).toBe(404);
  await expect(
    page.getByRole("heading", { name: "Record unavailable" }),
  ).toBeVisible();
  await expect(page.locator(".app-shell")).toHaveCount(0);
});
