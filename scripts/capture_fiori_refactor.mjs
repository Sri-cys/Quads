import { spawn } from "child_process";

const views = [
  { name: "refactor_dashboard_1440.png", url: "http://localhost:8000/" },
  { name: "refactor_cases_1440.png", url: "http://localhost:8000/#/cases" },
  { name: "refactor_new_disruption_1440.png", url: "http://localhost:8000/#/new-disruption" },
  { name: "refactor_impact_1440.png", url: "http://localhost:8000/#/impact/CASE-0001" },
  { name: "refactor_checkpoint1_1440.png", url: "http://localhost:8000/#/checkpoint1/CASE-0001" },
  { name: "refactor_recovery_1440.png", url: "http://localhost:8000/#/recovery/CASE-0001" },
  { name: "refactor_execution_1440.png", url: "http://localhost:8000/#/execution/CASE-0001" },
  { name: "refactor_monitoring_1440.png", url: "http://localhost:8000/#/monitoring/CASE-0001" },
  { name: "refactor_outcome_1440.png", url: "http://localhost:8000/#/outcome/CASE-0001" }
];

const artifactDir = "/Users/srisaran/.gemini/antigravity-ide/brain/f8df4094-77bd-4799-b703-30e6e0638d62";

async function run() {
  for (const v of views) {
    const outPath = `${artifactDir}/${v.name}`;
    console.log(`Capturing ${v.url} -> ${outPath}`);
    await new Promise((resolve) => {
      const p = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
        "--headless=new",
        "--disable-gpu",
        "--window-size=1440,900",
        "--virtual-time-budget=4000",
        `--screenshot=${outPath}`,
        v.url
      ]);
      p.on("close", () => resolve());
    });
    console.log(`Saved ${v.name}`);
  }
  console.log("All views captured successfully!");
}

run();
