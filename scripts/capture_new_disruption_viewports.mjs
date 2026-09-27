import { spawn } from "child_process";

const viewports = [
  { name: "fiori_new_disruption_1440.png", width: 1440, height: 900 },
  { name: "fiori_new_disruption_1280.png", width: 1280, height: 800 },
  { name: "fiori_new_disruption_1024.png", width: 1024, height: 768 }
];

const artifactDir = "/Users/srisaran/.gemini/antigravity-ide/brain/4a2ee235-6c50-44ca-9593-55b2b3de0609";
const url = "http://localhost:8000/#/new-disruption";

async function run() {
  for (const vp of viewports) {
    const outPath = `${artifactDir}/${vp.name}`;
    console.log(`Capturing ${url} at ${vp.width}x${vp.height} -> ${outPath}`);
    await new Promise((resolve) => {
      const p = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
        "--headless=new",
        "--disable-gpu",
        `--window-size=${vp.width},${vp.height}`,
        "--virtual-time-budget=3500",
        `--screenshot=${outPath}`,
        url
      ]);
      p.on("close", () => resolve());
    });
    console.log(`Saved ${vp.name}`);
  }
  console.log("All viewports captured!");
}

run();
