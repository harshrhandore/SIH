import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { login } from "./helpers";

test("student palette exposes navigation without general record searches", async ({
  page,
}) => {
  await login(page, "student.riya@example.test");
  let recordSearches = 0;
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/backend/students/search")
      recordSearches++;
  });
  await page
    .getByRole("button", { name: "Search workspace (Ctrl+K)", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Search workspace" });
  await page.getByLabel("Find a page or student").fill("Passport");
  await expect(
    dialog.getByRole("link", { name: "My Passport", exact: true }),
  ).toBeVisible();
  await expect(dialog.getByText("Students in your scope")).toHaveCount(0);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.keyboard.press("Escape");
  expect(recordSearches).toBe(0);
});

test("changing a query hides previous records while its request is pending", async ({
  page,
}) => {
  await login(page, "operator.a@example.test");
  await page.goto("/students");
  const input = page.getByRole("textbox", { name: "Search student records" });
  await input.fill("Riya Sharma");
  const previous = page.getByRole("link", { name: "Riya Sharma", exact: true });
  await expect(previous).toBeVisible();
  let started!: () => void;
  const requested = new Promise<void>((resolve) => {
    started = resolve;
  });
  let release!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/backend/students/search?*", async (route) => {
    if (
      new URL(route.request().url()).searchParams.get("q") ===
      "NoSuchSyntheticName"
    ) {
      started();
      await held;
    }
    await route.continue();
  });
  await input.fill("NoSuchSyntheticName");
  await requested;
  try {
    await expect(previous).not.toBeVisible();
    await expect(
      page.getByRole("status", { name: "Loading records" }),
    ).toBeVisible();
  } finally {
    release();
  }
  await expect(
    page.getByText("No records to display", { exact: true }),
  ).toBeVisible();
});
