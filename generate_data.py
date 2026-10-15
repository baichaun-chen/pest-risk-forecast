# -*- coding: utf-8 -*-
"""
生成《虫害监测与风险预测》模拟测试数据（每张表约 150 条）：
  data/监测点基础表.csv      150 个监测点
  data/虫情监测表.csv        150 条监测记录（75 个活跃点 × 2 次，含 5 条脏数据供清洗演示）
  data/气象数据表.csv        与虫情记录按 监测点+日期 对齐，150 条
  data/历史消杀记录表.csv    约 150 条（爆发后消杀 + 高风险预防性消杀）
  data/时间信息表.csv        覆盖全部日期（约 150 天候选日期池）
"""
import csv, math, os, random
from datetime import date, timedelta

random.seed(42)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)

RAINY_MONTHS = {4, 5, 6, 7, 8, 9}  # 南方雨季
CLIMATE = {
    1: (12, 62, 0.20, 8), 2: (14, 66, 0.25, 12), 3: (18, 72, 0.35, 25),
    4: (23, 78, 0.45, 60), 5: (27, 82, 0.50, 110), 6: (29, 85, 0.55, 160),
    7: (31, 84, 0.45, 140), 8: (31, 83, 0.45, 130), 9: (28, 80, 0.40, 90),
    10: (24, 72, 0.25, 40), 11: (19, 66, 0.18, 20), 12: (14, 62, 0.15, 10),
}
AREA_TYPES = ["仓储", "林地", "绿化带"]
VEG_BY_AREA = {
    "仓储": ["木包装堆存区", "竹木货架区", "空仓区"],
    "林地": ["松树林", "桉树林", "阔叶混交林"],
    "绿化带": ["灌木绿篱", "行道树带", "草花混合带"],
}
TRAP_PREFIX = {"仓储": "CC", "林地": "LD", "绿化带": "LH"}
PESTICIDES = ["拟除虫菊酯", "吡虫啉", "氟虫腈饵剂", "苏云金杆菌", "联苯菊酯"]

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

# ---------- 1. 监测点基础表：150 个 ----------
points = []
for i in range(1, 151):
    area = AREA_TYPES[(i - 1) % 3]
    points.append({
        "监测点ID": "MP%03d" % i,
        "区域类型": area,
        "植被类型": random.choice(VEG_BY_AREA[area]),
        "周边积水情况": random.choice(["有", "无"]),
        "是否靠近仓库": "是" if (area == "仓储" or random.random() < 0.3) else "否",
    })

# ---------- 候选日期池：150 天，偏暖季 ----------
pool = set()
while len(pool) < 150:
    m = random.choices(range(1, 13),
                       weights=[2, 2, 4, 8, 12, 14, 14, 14, 12, 8, 4, 2])[0]
    y = 2024 if m >= 6 else 2025
    if random.random() < 0.35:
        y = 2025 if m >= 6 else 2026
    d = date(y, m, random.randint(1, 28))
    if d <= date(2026, 6, 30):
        pool.add(d)
pool = sorted(pool)
all_dates = set(pool)

# ---------- 2/3. 虫情监测表 + 气象数据表：75 个活跃点 × 2 次 = 150 条 ----------
active = random.sample(points, 75)
monitor_rows, weather_rows = [], []
for p in active:
    days = sorted(random.sample(pool, 2))
    prev_density = random.randint(0, 8)
    for d in days:
        t0, h0, pr, r0 = CLIMATE[d.month]
        temp = round(random.gauss(t0, 2.0), 1)
        humid = round(min(98, max(35, random.gauss(h0, 6))), 1)
        rain = round(random.gammavariate(2.0, r0 / 8.0), 1) if random.random() < pr else 0.0
        dry_days = max(0, int(random.gauss(10 if rain == 0 else 2, 5)))
        weather_rows.append({
            "监测点ID": p["监测点ID"], "日期": d.isoformat(),
            "平均气温": temp, "相对湿度": humid,
            "降雨量": rain, "连续无雨天数": dry_days,
        })
        risk = (-10.8
                + 0.16 * temp + 0.05 * humid
                + 0.9 * (1 if p["周边积水情况"] == "有" else 0)
                + 0.8 * (1 if p["是否靠近仓库"] == "是" else 0)
                + 0.7 * (1 if p["区域类型"] == "林地" else 0)
                + 0.4 * (1 if p["区域类型"] == "仓储" else 0)
                + 0.01 * prev_density
                - 0.04 * dry_days
                + random.gauss(0, 0.5))
        prob = sigmoid(risk)
        outbreak = 1 if random.random() < prob else 0
        density = int(min(400, max(0, random.gauss(170, 45) if outbreak else random.gauss(40, 22))))
        monitor_rows.append({
            "监测点ID": p["监测点ID"], "监测日期": d.isoformat(),
            "虫口数量": density, "是否虫害爆发": outbreak,
            "诱捕器编号": "%s-%s-%02d" % (TRAP_PREFIX[p["区域类型"]], p["监测点ID"][2:], random.randint(1, 3)),
        })
        prev_density = density

# 注入脏数据：3 个缺失 + 2 个异常（-15 / 99999），供加分题清洗演示
dirty_idx = random.sample(range(len(monitor_rows)), 5)
monitor_rows[dirty_idx[0]]["虫口数量"] = ""
monitor_rows[dirty_idx[1]]["虫口数量"] = ""
monitor_rows[dirty_idx[2]]["虫口数量"] = ""
monitor_rows[dirty_idx[3]]["虫口数量"] = -15
monitor_rows[dirty_idx[4]]["虫口数量"] = 99999

# ---------- 4. 历史消杀记录表：约 150 条 ----------
disinfect_rows = []
did = 0
def next_pool(d):
    for pd in pool:
        if pd >= d:
            return pd
    return pool[-1]

def add_dis(pid, base_date, reactive):
    global did
    did += 1
    d = next_pool(base_date + timedelta(days=random.randint(0, 2)))  # 对齐到监测日期池
    rate = random.gauss(0.82 if reactive else 0.55, 0.1)  # 预防性消杀下降率低一些
    disinfect_rows.append({
        "记录ID": "SX%03d" % did,
        "监测点ID": pid, "消杀日期": d.isoformat(),
        "消杀药剂类型": random.choice(PESTICIDES),
        "消杀后虫口下降率": round(min(0.99, max(0.2, rate)), 2),
    })

for r in monitor_rows:
    v = r["虫口数量"]
    if not isinstance(v, int):
        continue
    d0 = date.fromisoformat(r["监测日期"])
    if r["是否虫害爆发"] == 1:
        add_dis(r["监测点ID"], d0, True)          # 爆发后消杀
        if random.random() < 0.35:
            add_dis(r["监测点ID"], d0 + timedelta(days=7), True)  # 复治
    elif v >= 90:
        add_dis(r["监测点ID"], d0, True)
    elif v >= 40 and random.random() < 0.8:
        add_dis(r["监测点ID"], d0, False)         # 高风险预防性消杀

# 例行消杀：60% 活跃点每点 1 次（植保服务商常规维护）
for p in random.sample(active, int(len(active) * 0.6)):
    add_dis(p["监测点ID"], random.choice(pool), False)

# ---------- 5. 时间信息表 ----------
time_rows = [{"日期": d.isoformat(), "月份": d.month,
              "是否雨季": 1 if d.month in RAINY_MONTHS else 0}
             for d in sorted(all_dates)]

def dump(name, rows, fields):
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(name, len(rows), "rows")

dump("监测点基础表.csv", points, ["监测点ID", "区域类型", "植被类型", "周边积水情况", "是否靠近仓库"])
dump("虫情监测表.csv", monitor_rows, ["监测点ID", "监测日期", "虫口数量", "是否虫害爆发", "诱捕器编号"])
dump("气象数据表.csv", weather_rows, ["监测点ID", "日期", "平均气温", "相对湿度", "降雨量", "连续无雨天数"])
dump("历史消杀记录表.csv", disinfect_rows, ["记录ID", "监测点ID", "消杀日期", "消杀药剂类型", "消杀后虫口下降率"])
dump("时间信息表.csv", time_rows, ["日期", "月份", "是否雨季"])

outbreaks = sum(1 for r in monitor_rows if r["是否虫害爆发"] == 1)
print("outbreak rate: %d/%d = %.2f" % (outbreaks, len(monitor_rows), outbreaks / len(monitor_rows)))
