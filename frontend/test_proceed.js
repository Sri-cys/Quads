const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
    page.on('pageerror', err => console.log('BROWSER ERROR:', err.message));
    
    await page.goto('http://localhost:8080/index.html#/recovery/CASE-0001');
    
    // Wait for the UI to load
    await page.waitForTimeout(3000);
    
    // Select a plan (the first ghost button)
    const selectBtns = await page.$$('button:has-text("Select Plan")');
    if (selectBtns.length > 0) {
        await selectBtns[0].click();
        await page.waitForTimeout(1000);
    }
    
    // Click proceed
    const proceedBtn = await page.$('#btnProceedDecisionBottom');
    if (proceedBtn) {
        console.log('Clicking proceed button...');
        await proceedBtn.click();
        await page.waitForTimeout(2000);
    } else {
        console.log('Proceed button not found!');
    }
    
    console.log('Current URL after click:', page.url());
    await browser.close();
})();
