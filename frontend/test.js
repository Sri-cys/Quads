const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({headless: "new"});
    const page = await browser.newPage();
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    await page.goto('http://localhost:8080/index.html');
    await page.evaluate(() => {
        localStorage.setItem('quads_priority_CASE-0001', 'BALANCED');
        localStorage.setItem('quads_selected_plan_CASE-0001', 'PLAN-001');
    });
    await page.goto('http://localhost:8080/index.html#/executionMonitoring/CASE-0001');
    await new Promise(r => setTimeout(r, 6000));
    await browser.close();
})();
