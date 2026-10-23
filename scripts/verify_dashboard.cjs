const { createRequire } = require("node:module");
const fs = require("node:fs/promises");
const path = require("node:path");
const { createHash } = require("node:crypto");
const req = createRequire(path.join(
  process.env.RUNTIME_NODE_MODULES ||
  "C:/Users/viraj/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules",
  "_gridshift_browser.cjs",
));
const { chromium } = req("playwright");

async function main() {
  const root = path.resolve(__dirname, "..");
  const output = path.join(root, "artifacts/tests");
  const completedResults = await fs.access(path.join(root, "artifacts/results.json"))
    .then(() => true, () => false);
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.GRIDSHIFT_BROWSER ||
      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  });
  const errors = [];
  try {
    for (const [name, viewport] of Object.entries({
      desktop: { width: 1440, height: 960 },
      mobile: { width: 390, height: 844 },
    })) {
      const page = await browser.newPage({ viewport });
      page.on("pageerror", error => errors.push(error.message));
      await page.goto("http://127.0.0.1:8501");
      await page.getByRole("heading", { name: "GridShift", exact: true }).waitFor();
      await page.locator('[data-testid="stMetric"]').first().waitFor();
      if (completedResults) {
        await page.getByText("Forecast-ranked start:", { exact: false }).waitFor();
        await page.getByRole("button", { name: "Download all candidate windows", exact: true }).waitFor();
        await page.locator('[data-testid="stPlotlyChart"] svg.main-svg').first().waitFor();
        await page.locator('[data-testid="stDataFrame"]').first().waitFor();
        if (await page.getByText("2025 test forecast is hidden", { exact: false }).count()) {
          throw new Error(`${name} completed results did not unlock the recommendation`);
        }
      }
      await page.screenshot({ path: path.join(output, `dashboard-${name}.png`), fullPage: true });
      const geometry = await page.evaluate(() => ({
        width: innerWidth, bodyWidth: document.body.scrollWidth,
        exceptions: document.querySelectorAll('[data-testid="stException"]').length,
      }));
      if (geometry.bodyWidth > geometry.width + 1 || geometry.exceptions) {
        throw new Error(`${name} overflow or Streamlit exception ${JSON.stringify(geometry)}`);
      }
      if (name === "desktop") {
        for (const view of ["Forecasts", "Model comparison", "Backtests", "Data and evidence"]) {
          await page.locator('[data-testid="stSidebar"]').getByText(view, { exact: true }).click();
          await page.getByRole("heading", { name: view, exact: true }).waitFor();
          if (completedResults && view === "Model comparison") {
            await page.getByRole("heading", { name: "Test metrics (recorded)", exact: true }).waitFor();
          }
          if (completedResults && view === "Backtests") {
            await page.getByRole("heading", { name: "Single-job primary summary", exact: true }).waitFor();
          }
          if (completedResults) {
            await page.locator('[data-testid="stDataFrame"]').first().waitFor();
          }
          await page.screenshot({
            path: path.join(output, `dashboard-${view.toLowerCase().replaceAll(" ", "-")}.png`),
            fullPage: true,
          });
          if (await page.locator('[data-testid="stException"]').count()) {
            throw new Error(`${view} has a Streamlit exception`);
          }
        }
      }
      await page.close();
    }
    if (errors.length) throw new Error(errors.join("\n"));
    const targets = ["app/streamlit_app.py", "scripts/verify_dashboard.cjs",
      ...(await fs.readdir(output)).filter(name => name.startsWith("dashboard-") && name.endsWith(".png"))
        .map(name => `artifacts/tests/${name}`)];
    if (completedResults) targets.push("artifacts/results.json", "artifacts/deployment/deployment.json");
    const fileHashes = {};
    for (const relative of targets) {
      fileHashes[relative] = createHash("sha256").update(await fs.readFile(path.join(root, relative))).digest("hex");
    }
    await fs.writeFile(path.join(output, "dashboard_browser.json"), JSON.stringify({
      passed: true, views: 5, desktop: [1440, 960], mobile: [390, 844],
      exceptions: errors, checked_at_utc: new Date().toISOString(),
      completed_results: completedResults,
      scope: "Local browser paths and layout; screenshots require visual review",
      file_hashes: fileHashes,
    }, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
