# -*- coding: utf-8 -*-
"""
生成三页站点：
  theory.html    —— 理论答卷（参考答案.md 的一/二/三大部分）
  dataset.html   —— 5 张表完整数据展示 + 导出 CSV（约 150 条/表）
  dashboard.html —— 由 build_dashboard.py 生成（动态看板）
"""
import csv, io, json, os, re

BASE = os.path.dirname(os.path.abspath(__file__))

NAV = """<nav>
  <span class="brand">虫害风险预测 · 模拟测试</span>
  <a href="index.html"%s>① 理论答卷</a>
  <a href="dataset.html"%s>② 数据集</a>
  <a href="dashboard.html"%s>③ 动态看板</a>
</nav>"""

CSS = """
:root{--bg:#0b1220;--panel:#131c2e;--panel2:#182239;--line:#263350;--txt:#e8eefc;
--dim:#8fa3c8;--accent:#4cc9f0;--accent2:#7b61ff;--good:#38d39f;--warn:#ffb454;--bad:#ff5d73}
*{margin:0;padding:0;box-sizing:border-box}
body{background:radial-gradient(1200px 600px at 80% -10%,#1b2b4d 0%,var(--bg) 55%);
color:var(--txt);font-family:"Microsoft YaHei","PingFang SC",sans-serif;min-height:100vh;padding:88px 18px 60px}
nav{position:fixed;top:0;left:0;right:0;z-index:99;display:flex;align-items:center;gap:6px;
padding:12px 26px;background:rgba(11,18,32,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
nav .brand{font-weight:800;font-size:15px;margin-right:22px;
background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;background-clip:text;color:transparent}
nav a{color:var(--dim);text-decoration:none;font-size:13px;padding:7px 16px;border-radius:8px;transition:.2s}
nav a:hover{color:var(--txt);background:#182239}
nav a.on{color:#06121f;background:linear-gradient(90deg,var(--accent),var(--accent2));font-weight:700}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:26px;letter-spacing:1px}
h1 span{background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--dim);margin-top:6px;font-size:13px}
.card{background:linear-gradient(160deg,var(--panel),var(--panel2));border:1px solid var(--line);
border-radius:14px;padding:22px 24px;margin-top:18px;box-shadow:0 8px 24px rgba(0,0,0,.35)}
.card h2{font-size:19px;margin-bottom:6px;color:var(--accent)}
.card h3{font-size:15px;margin:16px 0 8px;color:var(--txt)}
.card h3 .tag{display:inline-block;background:#0d1526;border:1px solid var(--line);color:var(--warn);
font-size:11px;border-radius:6px;padding:2px 8px;margin-right:8px;vertical-align:2px}
.card p{font-size:14px;line-height:1.9;color:#cdd9ef;margin:6px 0}
.card li{font-size:14px;line-height:1.9;color:#cdd9ef;margin-left:22px}
.card b{color:var(--txt)}
.card table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13px}
.card th{background:#0d1526;color:var(--accent);padding:8px 10px;border:1px solid var(--line);text-align:left}
.card td{padding:8px 10px;border:1px solid var(--line);color:#cdd9ef}
blockquote{border-left:3px solid var(--accent2);padding:8px 14px;background:#0d1526;border-radius:0 8px 8px 0;
color:var(--dim);font-size:13px;margin:10px 0;line-height:1.8}
pre{background:#0a1120;border:1px solid var(--line);border-radius:10px;padding:14px 16px;overflow:auto;
font-size:12.5px;line-height:1.7;color:#9fe8ff;margin:10px 0;font-family:Consolas,monospace}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}
.tab{background:#0d1526;border:1px solid var(--line);color:var(--dim);border-radius:9px;
padding:9px 18px;cursor:pointer;font-size:13px;transition:.2s}
.tab.on{color:#06121f;background:linear-gradient(90deg,var(--accent),var(--accent2));font-weight:700;border-color:transparent}
.stat{display:inline-block;background:#0d1526;border:1px solid var(--line);border-radius:8px;
padding:6px 14px;font-size:12px;color:var(--dim);margin:10px 10px 0 0}
.stat b{color:var(--accent);font-size:15px;margin-right:4px}
.dwrap{max-height:560px;overflow:auto;margin-top:12px;border:1px solid var(--line);border-radius:10px}
table.data{border-collapse:collapse;width:100%;font-size:12.5px}
table.data th{position:sticky;top:0;background:#182239;color:var(--accent);padding:8px 10px;
border-bottom:2px solid var(--accent2);text-align:left;white-space:nowrap;z-index:2}
table.data td{padding:6px 10px;border-bottom:1px solid #1b2740;color:#cdd9ef;white-space:nowrap}
table.data tr:nth-child(even) td{background:rgba(24,34,57,.45)}
table.data tr.hl td{background:rgba(255,93,115,.12);color:#ffb3be}
.btn{background:linear-gradient(90deg,var(--accent),var(--accent2));color:#06121f;border:0;border-radius:8px;
padding:8px 18px;font-weight:700;cursor:pointer;font-size:12.5px;margin-top:12px}
.btn:hover{filter:brightness(1.15)}
footer{margin-top:26px;color:var(--dim);font-size:12px;text-align:center}
@media(max-width:640px){
nav{padding:8px 12px;flex-wrap:wrap;gap:4px}
nav .brand{width:100%;margin:0 0 2px;font-size:13px}
nav a{padding:6px 10px;font-size:12px}
body{padding:100px 10px 40px}
h1{font-size:20px}
.card{padding:16px 14px}
.card p,.card li{font-size:13px}
.tabs{gap:6px}
.tab{padding:7px 12px;font-size:12px}
.dwrap{max-height:62vh}
table.data th,table.data td{padding:6px 8px;font-size:12px}
}
"""

def page(title, heading, subtitle, body, active):
    marks = [' class="on"' if i == active else '' for i in range(3)]
    return """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s</title><style>%s</style></head>
<body>%s
<div class="wrap">
<h1>%s</h1><div class="sub">%s</div>
%s
<footer>虫害监测与风险预测 · 模拟测试全套成果 · 理论答卷 / 数据集 / 动态看板</footer>
</div></body></html>""" % (title, CSS, NAV % tuple(marks), heading, subtitle, body)

# ---------- 极简 Markdown -> HTML ----------
def md_html(md):
    out, i, lines = [], 0, md.split("\n")
    in_code, buf = False, []
    in_list = False
    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False
    while i < len(lines):
        L = lines[i]
        if L.startswith("```"):
            if in_code:
                out.append("<pre>%s</pre>" % "\n".join(buf)
                           .replace("&", "&amp;").replace("<", "&lt;"))
                buf, in_code = [], False
            else:
                close_list(); in_code = True
            i += 1; continue
        if in_code:
            buf.append(L); i += 1; continue
        s = L.strip()
        if not s or s == "---":
            close_list(); i += 1; continue
        if s.startswith("|"):
            close_list()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().split("|")[1:-1]]
                if not all(re.match(r"^:?-{2,}:?$", c) for c in cells):
                    rows.append(cells)
                i += 1
            h = "<table><tr>%s</tr>" % "".join("<th>%s</th>" % c for c in rows[0])
            for r in rows[1:]:
                h += "<tr>%s</tr>" % "".join("<td>%s</td>" % fmt(c) for c in r)
            out.append(h + "</table>"); continue
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            close_list()
            lvl, txt = len(m.group(1)), m.group(2)
            tag = "h2" if lvl <= 2 else "h3"
            sm = re.match(r"^(\d+)\.\s*(.*?)（(.*?)）$", txt)
            if tag == "h3" and sm:
                txt = '<span class="tag">第 %s 题 · %s</span>%s' % (sm.group(1), sm.group(3), sm.group(2))
            out.append("<%s>%s</%s>" % (tag, fmt(txt), tag)); i += 1; continue
        if s.startswith(">"):
            close_list()
            out.append("<blockquote>%s</blockquote>" % fmt(s.lstrip("> "))); i += 1; continue
        if re.match(r"^[-*]\s+", s):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append("<li>%s</li>" % fmt(re.sub(r"^[-*]\s+", "", s))); i += 1; continue
        if re.match(r"^\d+\.\s+", s):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append("<li>%s</li>" % fmt(s)); i += 1; continue
        close_list()
        out.append("<p>%s</p>" % fmt(s)); i += 1
    close_list()
    return "\n".join(out)

def fmt(t):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)

# ---------- 第 1 页：理论答卷 ----------
with io.open(os.path.join(BASE, "参考答案.md"), encoding="utf-8") as f:
    md = f.read()
md_main = md.split("## 四、加分实操题")[0]
md_main = md_main.split("\n", 2)[2]  # 去掉 md 自身大标题与引言
sections = re.split(r"(?m)^## ", md_main)
theory_body = ""
for sec in sections:
    sec = sec.strip()
    if not sec:
        continue
    src = sec if sec.startswith(">") else "## " + sec
    theory_body += '<div class="card">' + md_html(src) + "</div>"
theory_body += """<div class="card"><h2>四、加分实操题</h2>
<p>该部分已单独制作成动态看板（ROC 动画 / 混淆矩阵 / 特征重要性 / 7 天预警窗口播放），
请前往 <a href="dashboard.html" style="color:var(--accent)">③ 动态看板</a> 查看；
标准答案代码见 <b>bonus_solution.py</b>（pandas + LightGBM），纯标准库实测见 <b>model_demo.py</b>。</p></div>"""

with io.open(os.path.join(BASE, "index.html"), "w", encoding="utf-8") as f:
    f.write(page("理论答卷｜虫害风险预测模拟测试",
                 "理论答卷 <span>简答 · 工程分析 · 上线监控</span>",
                 "一、简答题（40 分） · 二、建模工程分析题（35 分） · 三、模型上线与监控题（25 分）",
                 theory_body, 0))

# ---------- 第 2 页：数据集 ----------
TABLES = ["监测点基础表", "虫情监测表", "气象数据表", "历史消杀记录表", "时间信息表"]
DESCS = {
    "监测点基础表": "150 个监测点的静态属性（区域类型 / 植被 / 积水 / 近仓库）",
    "虫情监测表": "150 条监测记录（75 个活跃点 × 2 次），含 5 条脏数据供清洗演示；红色行为虫害爆发",
    "气象数据表": "150 条，与虫情记录按 监测点+日期 对齐",
    "历史消杀记录表": "136 条，含爆发后消杀、复治与预防性/例行消杀",
    "时间信息表": "150 天日期池，含月份与是否雨季标记",
}
datasets = {}
for name in TABLES:
    with io.open(os.path.join(BASE, "data", name + ".csv"), encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    datasets[name] = {"fields": rows[0], "rows": rows[1:], "desc": DESCS[name]}

tabs = "".join('<button class="tab%s" onclick="show(%d)">%s</button>'
               % (" on" if i == 0 else "", i, name) for i, name in enumerate(TABLES))
data_body = """
<div class="tabs">%s</div>
<div>
  <span class="stat"><b id="rn">-</b>数据行数</span>
  <span class="stat"><b id="cn">-</b>字段数</span>
  <span class="stat" id="ds" style="max-width:560px">-</span>
  <button class="btn" onclick="dl()">⬇ 导出当前表 CSV</button>
</div>
<div class="dwrap"><table class="data" id="tbl"></table></div>
<script>
const DS = %s;
const NAMES = %s;
let cur = 0;
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function show(i){
  cur = i;
  document.querySelectorAll('.tab').forEach((t,j)=>t.classList.toggle('on', j===i));
  const d = DS[NAMES[i]];
  document.getElementById('rn').textContent = d.rows.length;
  document.getElementById('cn').textContent = d.fields.length;
  document.getElementById('ds').textContent = d.desc;
  const ob = d.fields.indexOf('是否虫害爆发');
  let h = '<tr>' + d.fields.map(f=>'<th>'+esc(f)+'</th>').join('') + '</tr>';
  h += d.rows.map(r=>'<tr'+(ob>=0&&r[ob]==='1'?' class="hl"':'')+'>'
       + r.map(c=>'<td>'+esc(c)+'</td>').join('') + '</tr>').join('');
  document.getElementById('tbl').innerHTML = h;
}
function dl(){
  const d = DS[NAMES[cur]];
  const csv = '﻿' + [d.fields.join(',')].concat(d.rows.map(r=>r.join(','))).join('\\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
  a.download = NAMES[cur] + '.csv'; a.click();
}
show(0);
</script>""" % (tabs, json.dumps(datasets, ensure_ascii=False), json.dumps(TABLES, ensure_ascii=False))

with io.open(os.path.join(BASE, "dataset.html"), "w", encoding="utf-8") as f:
    f.write(page("数据集｜虫害风险预测模拟测试",
                 "数据集 <span>5 张表 · 每张约 150 条</span>",
                 "点击标签切换表格 · 红行为虫害爆发记录 · 支持一键导出 CSV（与 data/ 目录文件一致）",
                 data_body, 1))

print("index.html / dataset.html written")
