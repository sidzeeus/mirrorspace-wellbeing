import { defineConfig, devices } from "@playwright/test";

/**
 * Browser tests run against the production build (`next start`), because the service
 * worker and the real bundles only exist there. The API must be running:
 *
 *   docker compose up -d db redis web worker
 *   npm run build && npm run e2e
 */
const PORT = Number(process.env.E2E_PORT ?? 3000);

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
    ...devices["Pixel 7"],
  },
  webServer: {
    command: `npm run start -- --port ${PORT}`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: true,
    timeout: 60_000,
    env: { API_INTERNAL_URL: process.env.API_INTERNAL_URL ?? "http://localhost:8000" },
  },
});
