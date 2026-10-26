import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { login, manifest } from "./helpers";

const roles = [
  {
    name: "operator",
    email: "operator.a@example.test",
    routes: [
      "/dashboard",
      "/students",
      "/imports",
      "/imports/new",
      "/analytics",
    ],
  },
  {
    name: "officer",
    email: "officer@example.test",
    routes: [
      "/cases",
      "/students/" + manifest.showcase_student_id + "/timeline",
    ],
  },
  {
    name: "administrator",
    email: "admin@example.test",
    routes: ["/oversight", "/cases"],
  },
  {
    name: "student",
    email: "student.riya@example.test",
    routes: [
      "/students/" + manifest.showcase_student_id,
      "/students/" + manifest.showcase_student_id + "/timeline",
      "/certificates",
      "/career",
    ],
  },
];

for (const role of roles) {
  test(`${role.name} pages reflow without horizontal scrolling or redundant controls`, async ({
    page,
  }) => {
    await login(page, role.email);
    for (const route of role.routes) {
      await page.goto(route);
      await expect(page.locator("main.content h1")).toBeVisible();
      await expect(
        page.getByRole("status", { name: "Loading records", exact: true }),
      ).toHaveCount(0);
      await expect(page.locator("main.content .error")).toHaveCount(0);
      for (const width of [375, 768, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        const overflow = await page.evaluate(() => {
          const scrollers = [
            ...document.querySelectorAll<HTMLElement>("body *"),
          ]
            .filter((element) => {
              const style = getComputedStyle(element);
              return (
                element.clientWidth > 0 &&
                ["auto", "scroll"].includes(style.overflowX) &&
                element.scrollWidth > element.clientWidth + 1
              );
            })
            .map((element) => ({
              tag: element.tagName,
              className: element.className,
              width: element.clientWidth,
              content: element.scrollWidth,
            }));
          return {
            viewport: innerWidth,
            document: document.documentElement.scrollWidth,
            scrollers,
          };
        });
        expect(overflow.document, `${route} at ${width}px`).toBeLessThanOrEqual(
          overflow.viewport,
        );
        expect(overflow.scrollers, `${route} at ${width}px`).toEqual([]);
        await expect(
          page.getByRole("group", { name: "Table row density" }),
        ).toHaveCount(0);
        await expect(page.getByLabel("Rows per page")).toHaveCount(0);
        await expect(page.getByLabel("Advice per page")).toHaveCount(0);
        await expect(page.getByLabel("Aggregate institution")).toHaveCount(0);
        await expect(
          page.locator(
            ".scope-strip, .sidebar-bottom, .footer, .page-heading .eyebrow",
          ),
        ).toHaveCount(0);
        if (width === 375) {
          const accessibility = await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa"])
            .analyze();
          expect(accessibility.violations, route).toEqual([]);
        }
      }
    }
  });
}

test("narrow record layouts retain every labeled field and record link", async ({
  page,
}) => {
  await login(page, "operator.a@example.test");
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/students");
  await page
    .getByRole("textbox", { name: "Search student records" })
    .fill("Riya Sharma");
  const row = page.locator(".record-table tbody tr").first();
  await expect(
    row.getByRole("link", { name: "Riya Sharma", exact: true }),
  ).toBeVisible();
  await expect(row.getByRole("cell")).toHaveCount(5);
  for (const label of [
    "Student name",
    "Synthetic identifier",
    "Program",
    "Year",
    "Local status",
  ]) {
    await expect(row.locator(".cell-label", { hasText: label })).toBeVisible();
  }
  await row.getByRole("link", { name: "Riya Sharma", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Riya Sharma", exact: true }),
  ).toBeVisible();
});
