# -*- coding: utf-8 -*-
"""把 dashboard_data.json 注入模板，生成自包含的 dashboard.html。"""
import io, json

with io.open("dashboard_data.json", encoding="utf-8") as f:
    data = f.read()
with io.open("dashboard_template.html", encoding="utf-8") as f:
    tpl = f.read()
html = tpl.replace("__DATA__", data)
with io.open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
print("dashboard.html written,", len(html), "bytes")
