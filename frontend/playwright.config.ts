import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:4321",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    // Port 4321: ports 3000-3003 are occupied by Docker Desktop / Claude Code
    command: "npm run dev -- -p 4321",
    url: "http://localhost:4321",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
