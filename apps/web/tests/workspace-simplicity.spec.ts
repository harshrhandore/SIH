import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { login } from "./helpers";

test("login keeps demo account shortcuts optional", async ({ page }) => {
  let accountRequests = 0;
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/backend/auth/demo-accounts")
      accountRequests++;
  });
  await page.goto("/login");
  await expect(page.getByLabel("Email", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(page.getByRole("combobox")).not.toBeVisible();
  expect(accountRequests).toBe(0);

  const shortcuts = page.locator("summary", { hasText: "Demo accounts" });
  await shortcuts.focus();
  await page.keyboard.press("Enter");
  const account = page.getByRole("combobox", {
    name: "Demo account",
    exact: true,
  });
  await expect(account).toBeVisible();
  await account.selectOption("student.riya@example.test");
  await expect(page.getByLabel("Email", { exact: true })).toHaveValue(
    "student.riya@example.test",
  );
  await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
  await shortcuts.click();
  await expect(account).not.toBeVisible();
  await page.setViewportSize({ width: 375, height: 812 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
});

test("unavailable demo shortcuts do not block manual credentials", async ({
  page,
}) => {
  await page.route("**/api/backend/auth/demo-accounts", (route) =>
    route.abort(),
  );
  await page.goto("/login");
  await page.locator("summary", { hasText: "Demo accounts" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Demo accounts are unavailable",
  );
  await page
    .getByLabel("Email", { exact: true })
    .fill("operator.a@example.test");
  await page.getByLabel("Password", { exact: true }).fill("sample-password");
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeEnabled();
  await expect(page.locator(".login-form form").getByRole("alert")).toHaveCount(
    0,
  );
});

for (const [role, email] of [
  ["operator", "operator.a@example.test"],
  ["officer", "officer@example.test"],
  ["admin", "admin@example.test"],
  ["student", "student.riya@example.test"],
]) {
  test(`${role} navigation contains only workspace features`, async ({
    page,
  }) => {
    await login(page, email);
    const nav = page.getByRole("navigation", { name: "Workspace navigation" });
    await expect(nav).toBeVisible();
    await expect(
      nav.getByRole("link", { name: "Architecture", exact: true }),
    ).toHaveCount(0);
    await expect(
      nav.getByRole("link", { name: "Demo controls", exact: true }),
    ).toHaveCount(0);
    await page
      .getByRole("button", { name: "Search workspace (Ctrl+K)", exact: true })
      .click();
    const palette = page.getByRole("dialog", {
      name: "Search workspace",
      exact: true,
    });
    await expect(palette).toBeVisible();
    await expect(
      palette.getByRole("link", { name: "Architecture", exact: true }),
    ).toHaveCount(0);
    await expect(
      palette.getByRole("link", { name: "Demo controls", exact: true }),
    ).toHaveCount(0);
  });
}
