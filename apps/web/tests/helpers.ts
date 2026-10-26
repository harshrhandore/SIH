import { expect, type Page } from "@playwright/test";
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
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}
