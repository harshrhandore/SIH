import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test("unfinished terms show missing grades without invented zeroes", async ({
  page,
}) => {
  await login(page, "operator.a@example.test");
  const student = await page.evaluate(async () => {
    const search = await (
      await fetch("/api/backend/students/search?current_year=1")
    ).json();
    const candidate = search.items[0];
    const passport = await (
      await fetch("/api/backend/students/" + candidate.id)
    ).json();
    return { id: candidate.id, total: passport.profile.total_terms };
  });
  expect([6, 8]).toContain(student.total);
  let started!: () => void;
  const requested = new Promise<void>((resolve) => {
    started = resolve;
  });
  let release!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/backend/students/" + student.id, async (route) => {
    started();
    const response = await route.fetch();
    const packet = await response.json();
    await held;
    await route.fulfill({ response, json: { ...packet, projects: null } });
  });
  await page.goto("/students/" + student.id);
  await requested;
  try {
    await expect(
      page.getByRole("button", { name: "Print passport", exact: true }),
    ).toBeDisabled();
  } finally {
    release();
  }
  const rows = page.locator("#performance tbody tr");
  await expect(rows).toHaveCount(student.total);
  await expect(
    page.getByText(
      "This evidence section is unavailable. Other passport sections remain available.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Print passport", exact: true }),
  ).toBeVisible();
  await expect(rows.first()).toContainText("Not completed");
  await expect(
    rows.first().getByRole("cell").nth(2).locator(".cell-value"),
  ).toHaveText("—");
  await expect(
    rows.first().getByRole("cell").nth(3).locator(".cell-value"),
  ).toHaveText("—");
  await expect(
    rows.first().getByRole("cell").nth(4).locator(".cell-value"),
  ).toHaveText("—");
});
