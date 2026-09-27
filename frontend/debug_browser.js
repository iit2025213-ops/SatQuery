const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('BROWSER ERROR:', msg.text());
    }
  });

  page.on('pageerror', err => {
    console.log('PAGE ERROR:', err.toString());
  });

  console.log('Navigating to dashboard...');
  await page.goto('http://localhost:5173/dashboard?jobId=test', { waitUntil: 'networkidle0' }).catch(e => console.log('Goto error:', e.message));
  
  await new Promise(r => setTimeout(r, 2000));
  
  console.log('Navigating to analysis...');
  await page.goto('http://localhost:5173/analysis?jobId=test', { waitUntil: 'networkidle0' }).catch(e => console.log('Goto error:', e.message));
  
  await new Promise(r => setTimeout(r, 2000));
  
  await browser.close();
})();
