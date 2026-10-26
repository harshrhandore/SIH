import { test, expect } from "@playwright/test";
import { login, root } from "./helpers";
import path from "node:path";

test("analytics charts summarize scoped rows and preserve filter meaning", async ({
  page,
}) => {
  await login(page, "operator.a@example.test");
  await page.goto("/analytics");
  await expect(
    page.getByRole("img", { name: /Admissions by cohort/ }),
  ).toBeVisible();
  const admitted = await page.evaluate(async () => {
    const user = await (await fetch("/api/backend/auth/me")).json();
    const data = await (
      await fetch(
        "/api/backend/analytics/admissions?institution_id=" +
          user.institution_id,
      )
    ).json();
    return data.items.reduce(
      (sum: number, row: { admitted: number }) => sum + row.admitted,
      0,
    );
  });
  const plotted = (
    await page.locator(".chart-summary dd").allTextContents()
  ).reduce((sum, value) => sum + Number(value.replaceAll(",", "")), 0);
  expect(plotted).toBe(admitted);
  await page
    .getByRole("combobox", { name: "View", exact: true })
    .selectOption("placements");
  await expect(
    page.getByRole("img", { name: /Placement rate by graduation year/ }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "View", exact: true })
    .selectOption("performance");
  await page
    .getByRole("combobox", { name: "Year", exact: true })
    .selectOption("2023");
  await expect(
    page.getByRole("img", { name: /CGPA distribution/ }),
  ).toBeVisible();
  await expect(
    page.locator(".table-scroll tbody tr").first().getByRole("cell").first(),
  ).toHaveText("2023");
  await page
    .getByRole("combobox", { name: "View", exact: true })
    .selectOption("data-quality");
  await expect(
    page.getByRole("combobox", { name: "Year", exact: true }),
  ).toBeDisabled();
  await expect(page.getByRole("img", { name: /Record quality/ })).toBeVisible();
  await page.getByRole("button", { name: "Refresh now", exact: true }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Analytics refreshed at" }),
  ).toBeVisible({ timeout: 20000 });
  await page.screenshot({
    path: path.join(root, "docs/analytics-desktop.png"),
    fullPage: true,
  });
});
