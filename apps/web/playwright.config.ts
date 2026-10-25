import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests",
  timeout: 60000,
  fullyParallel: false,
  workers: 1,
  use: { baseURL: "http://localhost:3000", trace: "off", screenshot: "off" },
  reporter: [
    ["list"],
    ["json", { outputFile: "../../docs/playwright-results.json" }],
  ],
});
