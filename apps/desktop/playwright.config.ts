import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./playwright",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright/report", open: "never" }],
    ["json", { outputFile: "playwright/report/results.json" }],
  ],
  outputDir: "playwright/test-output",
  use: {
    baseURL: "http://127.0.0.1:4010",
    trace: "off",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "pnpm dev --hostname 127.0.0.1 --port 4010",
    url: "http://127.0.0.1:4010",
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
    stdout: "pipe",
    stderr: "pipe",
  },
});
