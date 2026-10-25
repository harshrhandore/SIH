import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
import path from "node:path";
const root = path.resolve(process.cwd(), "../..");
const env = Object.fromEntries(
  fs
    .readFileSync(path.join(root, ".env"), "utf8")
    .trim()
    .split(/\r?\n/)
    .filter((s) => s.includes("="))
    .map((s) => [s.slice(0, s.indexOf("=")), s.slice(s.indexOf("=") + 1)]),
);
const manifest = JSON.parse(
  fs.readFileSync(path.join(root, "fixtures/manifest.json"), "utf8"),
);
async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(env.DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}
test("operator ledger and real search MISS HIT", async ({ page }) => {
  await login(page, "operator.a@example.test");
  await expect(
    page.getByRole("heading", { name: "Institution ledger", exact: true }),
  ).toBeVisible();
  const initialA: Record<number, number> = {
    100000: 9000,
    50000: 4500,
    5000: 1000,
    200: 80,
  };
  await expect(
    page.getByText(
      (initialA[manifest.dataset_students] + 881).toLocaleString("en-IN"),
      { exact: true },
    ),
  ).toBeVisible();
  await page.goto("/students");
  await page
    .getByRole("textbox", { name: "Search student records" })
    .fill("Riya Sharma");
  await expect(page.getByText("Found", { exact: false })).toContainText(
    "1 record",
  );
  await expect(
    page.getByRole("link", { name: "Riya Sharma", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(root, "docs/search-desktop.png"),
    fullPage: true,
  });
});
test("student passport and career evidence", async ({ page }) => {
  await login(page, "student.riya@example.test");
  await expect(
    page.getByRole("heading", { name: "Riya Sharma", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("8.42", { exact: true }).first()).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Trust Score · 91 / 100" }),
  ).toBeVisible();
  await page.goto("/career");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(
    page.getByText(
      "Your evidenced skills cover 74 of 100 role-weight points.",
      { exact: false },
    ),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(root, "docs/career-desktop.png"),
    fullPage: true,
  });
});
test("passport and certificate trials use real backend", async ({ page }) => {
  await login(page, "student.riya@example.test");
  await page.goto("/certificates");
  await page
    .locator("input[type=file]")
    .setInputFiles(
      path.join(root, "fixtures/certificates/showcase-genuine.pdf"),
    );
  await page.getByRole("button", { name: "Verify local consistency" }).click();
  await expect(
    page.getByRole("heading", { name: "Local certificate consistency report" }),
  ).toBeVisible();
  await expect(page.getByText("95.00", { exact: false })).toBeVisible();
  await expect(page.getByText("PDF_TEXT", { exact: true })).toBeVisible();
  await expect(
    page.getByText(
      "Verification trial — excluded from accepted passport and Trust Score",
    ),
  ).toBeVisible();
});
test("admin masking and aggregate oversight", async ({ page }) => {
  await login(page, "admin@example.test");
  await expect(
    page.getByRole("heading", { name: "Institution oversight" }),
  ).toBeVisible();
  await page.goto("/cases");
  await expect(
    page.getByRole("heading", { name: "Verification cases" }),
  ).toBeVisible();
  await expect(page.locator("main")).not.toContainText(
    "riya.sharma@example.test",
  );
  await expect(page.locator("main")).not.toContainText("SYN-0000000000018");
});
test("375px mobile and axe on passport", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await login(page, "student.riya@example.test");
  await expect(
    page.getByRole("heading", { name: "Riya Sharma", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await expect(
    page.getByRole("link", { name: "Career Copilot" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  fs.writeFileSync(
    path.join(root, "docs/axe-results.json"),
    JSON.stringify(result.violations, null, 2),
  );
  expect(result.violations).toEqual([]);
  await page.screenshot({
    path: path.join(root, "docs/passport-mobile.png"),
    fullPage: true,
  });
});
test("print passport artifact", async ({ page }) => {
  await login(page, "student.riya@example.test");
  await page.goto("/students/" + manifest.showcase_student_id + "/print");
  await expect(
    page.getByRole("heading", { name: "Riya Sharma", exact: true }),
  ).toBeVisible();
  await page.emulateMedia({ media: "print" });
  await page.pdf({
    path: path.join(root, "docs/passport-print.pdf"),
    format: "A4",
    preferCSSPageSize: true,
    printBackground: true,
  });
});

test("concurrent expired requests use one refresh and strip caller authorization", async ({
  page,
  context,
}) => {
  await login(page, "operator.b@example.test");
  await context.addCookies([
    {
      name: "shiksham_access",
      value: "invalid-expired-test-token",
      domain: "localhost",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);
  let refreshes = 0;
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/backend/auth/refresh")
      refreshes++;
  });
  await page.goto("/students");
  await expect(
    page.getByRole("heading", { name: "Student search", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".user-menu")).toContainText("Demo Operator B");
  expect(refreshes).toBe(1);
  const identity = await page.evaluate(async () => {
    const response = await fetch("/api/backend/auth/me", {
      headers: { Authorization: "Bearer malicious-caller-header" },
    });
    return { status: response.status, data: await response.json() };
  });
  expect(identity.status).toBe(200);
  expect(identity.data.email).toBe("operator.b@example.test");
});
