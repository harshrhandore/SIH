import { test, expect } from "@playwright/test";
import { login } from "./helpers";

function syntheticId(counter: number) {
  const body = String(counter).padStart(12, "0");
  const digits = [...body].reverse().map(Number);
  const sum = digits.reduce((total, digit, index) => {
    const value = index % 2 === 0 ? digit * 2 : digit;
    return total + (value > 9 ? value - 9 : value);
  }, 0);
  return "SYN-" + body + ((10 - (sum % 10)) % 10);
}

test("source upload, reasoned correction, approval and timeline persist", async ({
  page,
}) => {
  test.setTimeout(180000);
  const key = Date.now();
  const enrollment = "SYN-BROWSER-" + key;
  const source = [
    "APAAR ID,Enrollment No,Student Name,DOB,Parent Name,Program,Admission Year,Year,Semester,SGPA,Credits,Email,Gender",
    `BAD,${enrollment},Synthetic Browser ${key},01/01/2004,,BTECH:CSE,2022,4,1,8,22,browser.${key}@example.test,UNDISCLOSED`,
  ].join("\n");
  await login(page, "operator.b@example.test");
  await page.goto("/imports/new");
  await page
    .locator('input[type="file"]')
    .setInputFiles({
      name: "synthetic-browser.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(source),
    });
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Continue to mapping", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Map source columns", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Preview 20 rows", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Preview the first 20 rows",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Validate 1 records", exact: true })
    .click();
  await expect(page.getByText("completed", { exact: true })).toBeVisible({
    timeout: 30000,
  });
  const caseId = await page.evaluate(async (value) => {
    const result = await (
      await fetch("/api/backend/cases?q=" + encodeURIComponent(value))
    ).json();
    return result.items[0]?.id;
  }, enrollment);
  expect(caseId).toBeTruthy();
  await login(page, "officer@example.test");
  await page.goto("/cases/" + caseId);
  await page
    .getByLabel(/Reason \(10/)
    .fill("Recheck the identifier against the synthetic source document.");
  await page
    .getByRole("button", { name: "REQUEST CORRECTION", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Decision recorded.");
  await login(page, "operator.b@example.test");
  await page.goto("/cases/" + caseId);
  await page
    .getByLabel(/Reason \(10/)
    .fill("Corrected the synthetic identifier from the source record.");
  await page
    .getByLabel("Corrected synthetic ID", { exact: true })
    .fill(syntheticId(Math.floor(key / 1000) + 9000000000));
  await page
    .getByRole("button", { name: "Save correction", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Correction saved.");
  await login(page, "officer@example.test");
  await page.goto("/cases/" + caseId);
  await page
    .getByLabel(/Reason \(10/)
    .fill("Reviewed the corrected synthetic identifier and resolved findings.");
  await page.getByRole("button", { name: "APPROVE", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Decision recorded.");
  await expect(page.getByText("approved", { exact: true })).toBeVisible();
  await page
    .getByRole("link", { name: "Open audit timeline", exact: false })
    .click();
  await expect(
    page.getByText("Full chain verified", { exact: false }),
  ).toBeVisible();
  await expect(page.locator(".timeline")).toContainText("REVIEW APPROVED");
  await expect(page.locator(".timeline")).toContainText("STUDENT CORRECTED");
});
