#!/usr/bin/env node
// render-pdf.js — Markdown → HTML → PDF pipeline
// Usage:
//   node scripts/render-pdf.js                    → manuscript.pdf (zh, with author)
//   node scripts/render-pdf.js --anonymous        → manuscript-anonymous.pdf (zh, anonymous)
//   node scripts/render-pdf.js --en               → manuscript-en.pdf (en, with author)
//   node scripts/render-pdf.js --en --anonymous   → manuscript-en-anonymous.pdf (en, anonymous)

const { execSync } = require('child_process');
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const paperDir = path.resolve(__dirname, '..');
const templatePath = path.join(__dirname, 'arxiv-template.html');
const tmpHtml = path.join(paperDir, '.tmp-manuscript.html');

const en = process.argv.includes('--en');
const anonymous = process.argv.includes('--anonymous');
const outputArg = process.argv.filter(a => a.endsWith('.pdf')).pop();

let defaultName;
if (en && anonymous) defaultName = 'manuscript-en-anonymous.pdf';
else if (en) defaultName = 'manuscript-en.pdf';
else if (anonymous) defaultName = 'manuscript-anonymous.pdf';
else defaultName = 'manuscript.pdf';

const outputPdf = outputArg ? path.resolve(outputArg) : path.join(paperDir, defaultName);

// --- Step 1: Assemble markdown
const asmScript = en ? 'scripts/assemble-en.sh' : 'scripts/assemble.sh';
const mdFile = en ? 'manuscript-en.md' : 'manuscript.md';
console.log('Assembling manuscript...');
execSync(`bash ${asmScript}`, { cwd: paperDir, stdio: 'inherit' });

// --- Step 2: Pandoc → HTML
const authorMeta = anonymous ? '' : (en ? 'Song Difei (宋涤非)' : '宋涤非 (Song Difei)');
const affilMeta = anonymous ? '' : (en ? 'Huaxin Consulting, Design, and Research Institute, Hangzhou 310052' : '华信咨询设计研究院有限公司，杭州 310052');
const titleMeta = en
  ? 'Engineering as Code: Bringing Software Engineering Methodology to Engineering Design'
  : 'Engineering as Code：将软件工程方法引入工程设计';

const crossrefMeta = en
  ? { tableTitle: 'Table', tblPrefix: 'Table' }
  : { tableTitle: '表', tblPrefix: '表' };
const metaJson = { title: titleMeta, author: authorMeta, affiliation: affilMeta, ...crossrefMeta };
const metaPath = path.join(paperDir, '.tmp-metadata.json');
fs.writeFileSync(metaPath, JSON.stringify(metaJson));

console.log('Pandoc → HTML...');
execSync(
  `pandoc ${mdFile} -o ${tmpHtml} --standalone --template ${templatePath} --metadata-file=${metaPath} --filter pandoc-crossref --citeproc --bibliography=refs.bib`,
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
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:10pt;text-align:center;width:100%"><span class="pageNumber"></span></div>',
  });

  await browser.close();
  fs.unlinkSync(tmpHtml);

  const sizeKB = (fs.statSync(outputPdf).size / 1024).toFixed(0);
  console.log(`Done: ${outputPdf} (${sizeKB} KB)`);
})();
