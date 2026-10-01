const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    await page.goto('http://localhost:8080/index.html#/recovery/CASE-0001', { waitUntil: 'networkidle0' });
    
    // Wait for the app to load
    await page.waitForTimeout(3000);
    
    // Select a plan
    console.log("Selecting plan...");
    const selectButtons = await page.$$("button.sapMBtnGhost");
    if (selectButtons.length > 0) {
        await selectButtons[0].click();
        console.log("Clicked Select Plan.");
    } else {
        console.log("No select button found.");
    }
    
    await page.waitForTimeout(1000);
    
    // Click PROCEED
    console.log("Clicking PROCEED...");
    const proceedBtn = await page.$("button.sapBtnPrimary");
    if (proceedBtn) {
        await proceedBtn.click();
        console.log("Clicked PROCEED TO FINAL DECISION.");
    } else {
        console.log("Proceed button not found.");
    }
    
    await page.waitForTimeout(3000);
    console.log("Current URL after click:", page.url());
    await browser.close();
})();
