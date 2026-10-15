// 把 参考答案.md + data/*.csv 样本 打包成 模拟测试_已完成.docx
// 复用原 docx 的骨架（/tmp/docx_extract），只替换 word/document.xml，用 PowerShell 重新压缩
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = __dirname;
const SKELETON = process.platform === 'win32' ? 'C:/Users/86135/AppData/Local/Temp/docx_extract' : '/tmp/docx_extract';

const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function run(text, { bold = false, size = 21 } = {}) {
  return `<w:r><w:rPr><w:rFonts w:eastAsia="微软雅黑" w:ascii="Calibri"/>${bold ? '<w:b/>' : ''}<w:sz w:val="${size}"/><w:szCs w:val="${size}"/></w:rPr><w:t xml:space="preserve">${esc(text)}</w:t></w:r>`;
}
function para(text, opts = {}) {
  const { bold = false, size = 21, indent = 0, spaceAfter = 80 } = opts;
  return `<w:p><w:pPr><w:spacing w:after="${spaceAfter}"/>${indent ? `<w:ind w:left="${indent}"/>` : ''}</w:pPr>${run(text, { bold, size })}</w:p>`;
}
function cell(text, bold = false) {
  return `<w:tc><w:tcPr><w:tcW w:w="2400" w:type="dxa"/></w:tcPr>${para(String(text), { bold, size: 18, spaceAfter: 20 })}</w:tc>`;
}
function table(rows) {
  const borders = `<w:tblPr><w:tblBorders>${['top','left','bottom','right','insideH','insideV'].map(b =>
    `<w:${b} w:val="single" w:sz="4" w:color="999999"/>`).join('')}</w:tblBorders></w:tblPr>`;
  const trs = rows.map((r, i) => `<w:tr>${r.map(c => cell(c, i === 0)).join('')}</w:tr>`).join('');
  return `<w:tbl>${borders}${trs}</w:tbl>`;
}

// ---- 解析 参考答案.md ----
const md = fs.readFileSync(path.join(ROOT, '参考答案.md'), 'utf8');
const body = [];
body.push(para('数据分析建模考题｜虫害监测与风险预测 —— 已完成答卷', { bold: true, size: 32, spaceAfter: 200 }));

const lines = md.split(/\r?\n/);
let i = 0, inCode = false, codeBuf = [];
const flushCode = () => {
  if (codeBuf.length) {
    for (const cl of codeBuf) body.push(para(cl, { size: 18, indent: 360, spaceAfter: 20 }));
    codeBuf = [];
  }
};
while (i < lines.length) {
  const L = lines[i];
  if (L.startsWith('```')) {
    if (inCode) { inCode = false; flushCode(); } else { inCode = true; codeBuf = []; }
    i++; continue;
  }
  if (inCode) { codeBuf.push(L); i++; continue; }
  if (/^\s*$/.test(L) || /^---+$/.test(L) || /^>/.test(L)) { i++; continue; }
  // markdown 表格
  if (L.startsWith('|')) {
    const rows = [];
    while (i < lines.length && lines[i].startsWith('|')) {
      const cells = lines[i].split('|').slice(1, -1).map(s => s.trim());
      if (!cells.every(c => /^:?-{2,}:?$/.test(c))) rows.push(cells);
      i++;
    }
    if (rows.length) body.push(table(rows));
    continue;
  }
  const h = L.match(/^(#{1,4})\s+(.*)/);
  if (h) {
    const lvl = h[1].length;
    body.push(para(h[2], { bold: true, size: { 1: 30, 2: 26, 3: 23, 4: 22 }[lvl], spaceAfter: 120 }));
    i++; continue;
  }
  const cleaned = L.replace(/\*\*(.+?)\*\*/g, '$1').replace(/^[-*]\s+/, '· ').replace(/^\d+\.\s+/, m => m);
  body.push(para(cleaned, { indent: /^(·|\d)/.test(cleaned) ? 240 : 0 }));
  i++;
}

// ---- 附：测试数据样本 ----
body.push(para('附：测试数据说明（完整 150 条见 data/ 目录 CSV 文件）', { bold: true, size: 26, spaceAfter: 120 }));
const csvFiles = ['监测点基础表.csv', '虫情监测表.csv', '气象数据表.csv', '历史消杀记录表.csv', '时间信息表.csv'];
for (const f of csvFiles) {
  const raw = fs.readFileSync(path.join(ROOT, 'data', f), 'utf8').replace(/^﻿/, '');
  const rows = raw.trim().split(/\r?\n/).map(r => r.split(','));
  body.push(para(`${f.replace('.csv', '')}（共 ${rows.length - 1} 条，前 8 条样本）`, { bold: true, size: 22, spaceAfter: 60 }));
  body.push(table(rows.slice(0, 9)));
  body.push(para('', { spaceAfter: 120 }));
}

const documentXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>${body.join('')}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body>
</w:document>`;

if (!fs.existsSync(SKELETON)) {
  console.error('skeleton not found: ' + SKELETON);
  process.exit(1);
}
fs.writeFileSync(path.join(SKELETON, 'word', 'document.xml'), documentXml, 'utf8');

const outZip = path.join(ROOT, 'out_tmp.zip');
const outDocx = path.join(ROOT, '模拟测试_已完成.docx');
if (fs.existsSync(outZip)) fs.unlinkSync(outZip);
execSync(`powershell -NoProfile -Command "Compress-Archive -Path '${SKELETON.replace(/\//g, '\\')}\\*' -DestinationPath '${outZip.replace(/\//g, '\\')}' -Force"`);
fs.renameSync(outZip, outDocx);
console.log('written:', outDocx, fs.statSync(outDocx).size, 'bytes');
