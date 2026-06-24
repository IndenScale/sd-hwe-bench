#!/usr/bin/env node
// render-pdf.js — Markdown → HTML → PDF pipeline
// Usage:
//   node build/scripts/render-pdf.js                    → dist/pdf/<zh-slug>.pdf
//   node build/scripts/render-pdf.js --anonymous        → dist/pdf/<zh-slug>-anonymous.pdf
//   node build/scripts/render-pdf.js --en               → dist/pdf/<en-slug>.pdf
//   node build/scripts/render-pdf.js --en --anonymous   → dist/pdf/<en-slug>-anonymous.pdf

const { execSync } = require('child_process');
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const paperDir = path.resolve(__dirname, '../..');
const scriptDir = path.join(paperDir, 'build/scripts');
const templatePath = path.join(paperDir, 'build/templates/arxiv-template.html');
const tmpHtml = path.join(paperDir, '.tmp-manuscript.html');

const en = process.argv.includes('--en');
const anonymous = process.argv.includes('--anonymous');
const outputArg = process.argv.filter(a => a.endsWith('.pdf')).pop();

const sectionsDir = path.join(paperDir, en ? 'src/sections-en' : 'src/sections');

function getSlug(dir) {
  return execSync(`python3 "${path.join(scriptDir, 'slug-from-meta.py')}" "${dir}"`, {
    cwd: paperDir,
    encoding: 'utf-8',
  }).trim();
}

const slug = getSlug(sectionsDir);

const outputPdf = outputArg
  ? path.resolve(outputArg)
  : path.join(paperDir, 'dist/pdf', `${slug}${anonymous ? '-anonymous' : ''}.pdf`);
const mdFile = path.join(paperDir, 'dist/md', `${slug}.md`);

const asmScript = en ? 'build/scripts/assemble-en.sh' : 'build/scripts/assemble.sh';

console.log('Assembling markdown...');
execSync(`bash ${asmScript}`, { cwd: paperDir, stdio: 'inherit' });

// --- Step 2: Pandoc → HTML
const crossrefMeta = en
  ? { tableTitle: 'Table', tblPrefix: 'Table' }
  : { tableTitle: '表', tblPrefix: '表' };
const metaJson = { ...crossrefMeta };
const metaPath = path.join(paperDir, '.tmp-metadata.json');
fs.writeFileSync(metaPath, JSON.stringify(metaJson));

console.log('Pandoc → HTML...');
execSync(
  `pandoc "${mdFile}" -o "${tmpHtml}" --standalone --template "${templatePath}" --metadata-file="${metaPath}" --filter pandoc-crossref --citeproc --bibliography=refs.bib`,
  { cwd: paperDir, stdio: 'inherit' }
);
fs.unlinkSync(metaPath);

// --- Step 3: HTML → PDF with Playwright
(async () => {
  console.log('Rendering PDF...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const htmlContent = fs.readFileSync(tmpHtml, 'utf-8');
  await page.setContent(htmlContent, { waitUntil: 'networkidle' });

  await page.pdf({
    path: outputPdf,
    format: 'A4',
    margin: { top: '2.5cm', bottom: '2.5cm', left: '2cm', right: '2cm' },
    printBackground: false,
    displayHeaderFooter: false,
  });

  await browser.close();
  fs.unlinkSync(tmpHtml);

  const sizeKB = (fs.statSync(outputPdf).size / 1024).toFixed(0);
  console.log(`Done: ${outputPdf} (${sizeKB} KB)`);
})();
