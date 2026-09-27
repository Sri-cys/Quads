import { spawn } from "child_process";
import fs from "fs";

const views = [
  { name: "fiori_dashboard_final.png", url: "http://localhost:8000/" },
  { name: "fiori_cases_final.png", url: "http://localhost:8000/#/cases" },
  { name: "fiori_new_disruption_final.png", url: "http://localhost:8000/#/new-disruption" },
  { name: "fiori_impact_final.png", url: "http://localhost:8000/#/impact/CASE-0001" },
  { name: "fiori_checkpoint1_final.png", url: "http://localhost:8000/#/checkpoint1/CASE-0001" }
];

const artifactDir = "/Users/srisaran/.gemini/antigravity-ide/brain/4a2ee235-6c50-44ca-9593-55b2b3de0609";

async function run() {
  for (const v of views) {
    const outPath = `${artifactDir}/${v.name}`;
    console.log(`Capturing ${v.url} -> ${outPath}`);
    await new Promise((resolve) => {
      const p = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
        "--headless=new",
        "--disable-gpu",
        "--window-size=1440,900",
        "--virtual-time-budget=3500",
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
