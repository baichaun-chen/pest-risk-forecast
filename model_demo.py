# -*- coding: utf-8 -*-
"""
加分题实测（当前环境无 pandas / LightGBM，用纯标准库复现相同流程）：
1. 读取虫情数据，处理缺失值、异常虫口数量
2. 构造时序衍生特征：近7天平均虫口密度、近14天最大虫口数量、连续高湿天数
3. 按时序切分训练 / 验证集（前 80% 日期训练，后 20% 验证）
4. 训练二分类模型（逻辑回归，代替 LightGBM 演示流程），输出 AUC / Precision / Recall
5. 输出特征重要性（排列重要性 Permutation Importance）
"""
import csv, math, os, random
from collections import defaultdict
from datetime import date, timedelta

random.seed(7)
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def load(name):
    with open(os.path.join(BASE, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

monitor = load("虫情监测表.csv")
points = {r["监测点ID"]: r for r in load("监测点基础表.csv")}
weather = {(r["监测点ID"], r["日期"]): r for r in load("气象数据表.csv")}
timeinfo = {r["日期"]: r for r in load("时间信息表.csv")}
disinfect = load("历史消杀记录表.csv")

# ---------- 1. 数据清洗 ----------
clean, dropped = [], 0
for r in monitor:
    v = r["虫口数量"]
    if v == "" or v is None:            # 缺失
        dropped += 1
        continue
    v = float(v)
    if v < 0 or v > 10000:              # 异常（负值 / 超大值）
        dropped += 1
        continue
    r["虫口数量"] = v
    clean.append(r)
print("clean: kept %d, dropped %d (missing/abnormal)" % (len(clean), dropped))

# ---------- 2. 时序衍生特征（仅用当前日期之前的历史，防止数据泄漏） ----------
hist = defaultdict(list)   # 监测点 -> [(date, density)]
whist = defaultdict(list)  # 监测点 -> [(date, humidity)]
dhist = defaultdict(list)  # 监测点 -> [消杀date]
for r in sorted(clean, key=lambda x: x["监测日期"]):
    hist[r["监测点ID"]].append((date.fromisoformat(r["监测日期"]), r["虫口数量"]))
for r in load("气象数据表.csv"):
    whist[r["监测点ID"]].append((date.fromisoformat(r["日期"]), float(r["相对湿度"])))
for r in disinfect:
    dhist[r["监测点ID"]].append(date.fromisoformat(r["消杀日期"]))
for k in whist:
    whist[k].sort()
for k in dhist:
    dhist[k].sort()

def features(r):
    pid, d = r["监测点ID"], date.fromisoformat(r["监测日期"])
    p = points[pid]
    w = weather.get((pid, r["监测日期"]))
    t = timeinfo.get(r["监测日期"], {"月份": d.month, "是否雨季": 1 if d.month in (4,5,6,7,8,9) else 0})
    past = [(hd, v) for hd, v in hist[pid] if hd < d]
    near7 = [v for hd, v in past if hd >= d - timedelta(days=7)]
    near14 = [v for hd, v in past if hd >= d - timedelta(days=14)]
    humid_days = 0                       # 连续高湿天数（湿度>=80，向前回溯）
    for hd, h in sorted(whist[pid], reverse=True):
        if hd >= d:
            continue
        if h >= 80 and hd >= d - timedelta(days=30):
            humid_days += 1
        else:
            break
    recent_dis = sum(1 for dd in dhist[pid] if d - timedelta(days=30) <= dd < d)
    return [
        float(w["平均气温"]) if w else 22.0,
        float(w["相对湿度"]) if w else 70.0,
        float(w["降雨量"]) if w else 0.0,
        float(w["连续无雨天数"]) if w else 5.0,
        1.0 if p["周边积水情况"] == "有" else 0.0,
        1.0 if p["是否靠近仓库"] == "是" else 0.0,
        1.0 if p["区域类型"] == "林地" else 0.0,
        1.0 if p["区域类型"] == "仓储" else 0.0,
        float(t["月份"]),
        float(t["是否雨季"]),
        sum(near7) / len(near7) if near7 else 0.0,      # 近7天平均虫口密度
        max(near14) if near14 else 0.0,                 # 近14天最大虫口数量
        float(humid_days),                              # 连续高湿天数
        float(recent_dis),                              # 近30天消杀次数
    ]

FEAT_NAMES = ["平均气温", "相对湿度", "降雨量", "连续无雨天数", "周边积水", "靠近仓库",
              "区域_林地", "区域_仓储", "月份", "是否雨季",
              "近7天平均虫口密度", "近14天最大虫口数量", "连续高湿天数", "近30天消杀次数"]

rows = sorted(clean, key=lambda x: x["监测日期"])
X = [features(r) for r in rows]
y = [int(r["是否虫害爆发"]) for r in rows]

# ---------- 3. 按时序切分 ----------
cut = int(len(rows) * 0.8)
cut_date = rows[cut]["监测日期"]
Xtr, Xte, ytr, yte = X[:cut], X[cut:], y[:cut], y[cut:]
print("temporal split: train %d (pos %d), valid %d (pos %d), cut at %s"
      % (len(Xtr), sum(ytr), len(Xte), sum(yte), cut_date))

# ---------- 4. 逻辑回归（标准化 + 批量梯度下降） ----------
def standardize(Xtr, Xte):
    n = len(Xtr[0])
    mu = [sum(r[j] for r in Xtr) / len(Xtr) for j in range(n)]
    sd = [max(1e-9, (sum((r[j] - mu[j]) ** 2 for r in Xtr) / len(Xtr)) ** 0.5) for j in range(n)]
    f = lambda X: [[(r[j] - mu[j]) / sd[j] for j in range(n)] for r in X]
    return f(Xtr), f(Xte)

Xtr_s, Xte_s = standardize(Xtr, Xte)
n_feat = len(FEAT_NAMES)
wgt = [0.0] * n_feat
bias = 0.0
lr, epochs = 0.3, 800
pos_w = (len(ytr) - sum(ytr)) / max(1, sum(ytr))   # 类别不平衡加权
for ep in range(epochs):
    gw = [0.0] * n_feat
    gb = 0.0
    for xi, yi in zip(Xtr_s, ytr):
        z = bias + sum(wj * xj for wj, xj in zip(wgt, xi))
        p = 1.0 / (1.0 + math.exp(-max(-30, min(30, z))))
        err = (p - yi) * (pos_w if yi == 1 else 1.0)
        for j in range(n_feat):
            gw[j] += err * xi[j]
        gb += err
    m = len(Xtr_s)
    for j in range(n_feat):
        wgt[j] -= lr * gw[j] / m
    bias -= lr * gb / m

def predict(Xs):
    out = []
    for xi in Xs:
        z = bias + sum(wj * xj for wj, xj in zip(wgt, xi))
        out.append(1.0 / (1.0 + math.exp(-max(-30, min(30, z)))))
    return out

def auc(scores, labels):
    pairs = sorted(zip(scores, labels))
    rank_sum = sum(i + 1 for i, (_, l) in enumerate(pairs) if l == 1)
    npos, nneg = sum(labels), len(labels) - sum(labels)
    return (rank_sum - npos * (npos + 1) / 2) / (npos * nneg)

pte = predict(Xte_s)
pred = [1 if s >= 0.5 else 0 for s in pte]
tp = sum(1 for p_, l in zip(pred, yte) if p_ == 1 and l == 1)
fp = sum(1 for p_, l in zip(pred, yte) if p_ == 1 and l == 0)
fn = sum(1 for p_, l in zip(pred, yte) if p_ == 0 and l == 1)
precision = tp / max(1, tp + fp)
recall = tp / max(1, tp + fn)
print("AUC=%.3f  Precision=%.3f  Recall=%.3f" % (auc(pte, yte), precision, recall))

# ---------- 5. 排列重要性（验证集 AUC 下降幅度） ----------
base_auc = auc(pte, yte)
imp = []
for j in range(n_feat):
    Xp = [row[:] for row in Xte_s]
    col = [row[j] for row in Xp]
    random.shuffle(col)
    for row, v in zip(Xp, col):
        row[j] = v
    imp.append((FEAT_NAMES[j], base_auc - auc(predict(Xp), yte)))
imp.sort(key=lambda x: -x[1])
print("feature importance (permutation, AUC drop):")
for name, v in imp:
    print("  %-18s %.4f" % (name, v))
