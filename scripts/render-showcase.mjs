#!/usr/bin/env node

/**
 * Render showcase.html to a crisp PNG for LinkedIn.
 *
 * Usage:
 *   node scripts/render-showcase.mjs [input.html] [output.png]
 *
 * Defaults:
 *   input:  showcase.html (in current directory)
 *   output: showcase.png  (in current directory)
 *
 * Requires puppeteer (auto-installed via npx if not present).
 * First run downloads Chromium (~280MB) — subsequent runs are instant.
 */

import { resolve } from 'path';

const input = resolve(process.argv[2] || 'showcase.html');
const output = resolve(process.argv[3] || 'showcase.png');

async function render() {
  let puppeteer;
  try {
    puppeteer = await import('puppeteer');
  } catch {
    console.log('Installing puppeteer (first time only)...');
    const { execSync } = await import('child_process');
    execSync('npm install puppeteer', { stdio: 'inherit' });
    puppeteer = await import('puppeteer');
  }

  const browser = await puppeteer.default.launch({ headless: 'new' });
  const page = await browser.newPage();

  // 2x device scale for crisp retina output
  await page.setViewport({ width: 1080, height: 680, deviceScaleFactor: 2 });

  // Wait for fonts to load (Google Fonts)
  await page.goto(`file://${input}`, { waitUntil: 'networkidle0', timeout: 15000 });

  // Extra wait for font rendering
  await new Promise(r => setTimeout(r, 1000));

  // Clip to the .slide element so we capture exactly its dimensions
  const slide = await page.$('.slide');
  const box = await slide.boundingBox();
  await page.screenshot({ path: output, type: 'png', clip: box });
  await browser.close();

  console.log(`\n  Showcase saved: ${output}`);
  console.log(`  Dimensions: ${Math.round(box.width * 2)}x${Math.round(box.height * 2)} (2x retina)\n`);
}

render().catch(err => {
  console.error('Render failed:', err.message);
  process.exit(1);
});
