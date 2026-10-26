import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
export const root = path.resolve(process.cwd(), "../..");
const env = Object.fromEntries(
  fs
    .readFileSync(path.join(root, ".env"), "utf8")
    .trim()
    .split(/\r?\n/)
    .filter((s) => s.includes("="))
    .map((s) => [s.slice(0, s.indexOf("=")), s.slice(s.indexOf("=") + 1)]),
);
export const manifest = JSON.parse(
  fs.readFileSync(path.join(root, "fixtures/manifest.json"), "utf8"),
);
export async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(env.DEMO_PASSWORD);
  const submit = async () => {
    const response = page.waitForResponse(
      (reply) =>
        new URL(reply.url()).pathname === "/api/backend/auth/login" &&
        reply.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    return response;
  };
  let response = await submit();
  if (response.status() === 429) {
    // Suites reuse a small set of demo accounts. Honor the real server's limit.
    const seconds = Number(response.headers()["retry-after"] || 60);
    const cooldown =
      (Number.isFinite(seconds) ? Math.min(60, Math.max(1, seconds)) : 60) *
      1000;
    const info = test.info();
    info.setTimeout(info.timeout + cooldown + 10000);
    await page.waitForTimeout(cooldown);
    response = await submit();
  }
  expect(
    response.ok(),
    "Demo login must succeed with the real backend",
  ).toBeTruthy();
  await expect(page).not.toHaveURL(/\/login$/);
}
