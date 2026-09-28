import { spawn } from "child_process";

const views = [
  { name: "case0009_stage1_overview.png",    url: "http://localhost:8000/#case/CASE-0009" },
  { name: "case0009_stage2_impact.png",      url: "http://localhost:8000/#impact/CASE-0009" },
  { name: "case0009_stage3_priority.png",    url: "http://localhost:8000/#checkpoint1/CASE-0009" },
  { name: "case0009_stage4_constraints.png", url: "http://localhost:8000/#constraints/CASE-0009" },
  { name: "case0009_stage5_recovery.png",    url: "http://localhost:8000/#recovery/CASE-0009" },
  { name: "case0009_stage6_decision.png",    url: "http://localhost:8000/#decision/CASE-0009" },
  { name: "case0009_stage7_execution.png",   url: "http://localhost:8000/#execution/CASE-0009" }
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
        "--virtual-time-budget=3500",
        `--screenshot=${outPath}`,
        v.url
      ]);
      p.on("close", () => resolve());
    });
    console.log(`Saved ${v.name}`);
  }
  console.log("All CASE-0009 views captured successfully!");
}

run();
