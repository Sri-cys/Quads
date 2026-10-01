const puppeteer = require('/tmp/node_modules/puppeteer');
(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    await page.goto('http://localhost:8080/index.html', {waitUntil: 'networkidle0'});
    await page.evaluate(() => { localStorage.setItem('quads_selected_plan_CASE-0001', 'PLAN-05'); });
    // also set completedStage to 4 so we don't get redirected!
    await page.evaluate(() => { localStorage.setItem('quads_wf_CASE-0001', '4'); });

    await page.goto('http://localhost:8080/index.html#/decision/CASE-0001', {waitUntil: 'networkidle2'});
    await new Promise(r => setTimeout(r, 2000));
    
    console.log("Current URL:", page.url());
    const html = await page.content();
    const match = html.match(/data-state="([^"]+)"/g);
    console.log("States found:", match);
    await browser.close();
})();
