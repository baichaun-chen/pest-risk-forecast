# -*- coding: utf-8 -*-
"""从 model_demo 的运行结果导出看板所需 JSON（复用其全部计算）。"""
import io, json, contextlib
import model_demo as m

# ROC 曲线点
pairs = sorted(zip(m.pte, m.yte), key=lambda x: -x[0])
npos, nneg = sum(m.yte), len(m.yte) - sum(m.yte)
roc, tp, fp = [(0.0, 0.0)], 0, 0
for s, l in pairs:
    if l == 1: tp += 1
    else: fp += 1
    roc.append((round(fp / nneg, 4), round(tp / npos, 4)))
roc.append((1.0, 1.0))

data = {
    "metrics": {
        "auc": round(m.auc(m.pte, m.yte), 3),
        "precision": round(m.precision, 3),
        "recall": round(m.recall, 3),
        "kept": len(m.clean), "dropped": m.dropped, "total": len(m.monitor),
        "trainN": len(m.ytr), "trainPos": sum(m.ytr),
        "validN": len(m.yte), "validPos": sum(m.yte),
        "cutDate": m.cut_date,
    },
    "confusion": {"tp": m.tp, "fp": m.fp, "fn": m.fn,
                  "tn": len(m.yte) - m.tp - m.fp - m.fn},
    "roc": roc,
    "importance": [{"name": n, "value": round(max(0, v), 4)} for n, v in m.imp],
    "series": [{"date": r["监测日期"], "density": r["虫口数量"],
                "outbreak": int(r["是否虫害爆发"]), "point": r["监测点ID"]}
               for r in m.rows],
}
with io.open("dashboard_data.json", "w", encoding="utf-8") as f:
    f.write(json.dumps(data, ensure_ascii=False))
print("exported", len(roc), "roc points,", len(m.rows), "series points")
