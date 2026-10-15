# -*- coding: utf-8 -*-
"""
加分实操题 · 标准参考答案（需要 pandas / lightgbm / scikit-learn 环境）
流程：读取虫情数据 -> 清洗缺失与异常 -> 构造时序衍生特征 ->
      按时序切分 -> 训练 LightGBM -> 输出 AUC / Precision / Recall / 特征重要性
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, precision_score, recall_score

# ---------- 1. 读取数据 + 处理缺失值、异常虫口数量 ----------
monitor = pd.read_csv("data/虫情监测表.csv")
points = pd.read_csv("data/监测点基础表.csv")
weather = pd.read_csv("data/气象数据表.csv")
timeinfo = pd.read_csv("data/时间信息表.csv")
disinfect = pd.read_csv("data/历史消杀记录表.csv")

monitor["虫口数量"] = pd.to_numeric(monitor["虫口数量"], errors="coerce")
before = len(monitor)
monitor = monitor.dropna(subset=["虫口数量"])                 # 缺失值：删除（占比极小）
monitor = monitor[(monitor["虫口数量"] >= 0) & (monitor["虫口数量"] <= 10000)]  # 异常值：负值/超大值剔除
print(f"清洗：{before} -> {len(monitor)} 行")

monitor["监测日期"] = pd.to_datetime(monitor["监测日期"])
weather["日期"] = pd.to_datetime(weather["日期"])
disinfect["消杀日期"] = pd.to_datetime(disinfect["消杀日期"])

# ---------- 2. 构造时序衍生特征（只用当前日期之前的数据，防止泄漏） ----------
monitor = monitor.sort_values(["监测点ID", "监测日期"])
g = monitor.groupby("监测点ID")["虫口数量"]
monitor["近7天平均虫口密度"] = (
    g.apply(lambda s: s.rolling(7, min_periods=1).mean().shift(1)).reset_index(level=0, drop=True))
monitor["近14天最大虫口数量"] = (
    g.apply(lambda s: s.rolling(14, min_periods=1).max().shift(1)).reset_index(level=0, drop=True))

weather = weather.sort_values(["监测点ID", "日期"])
weather["高湿标记"] = (weather["相对湿度"] >= 80).astype(int)
def streak(s):
    out, c = [], 0
    for v in s:
        c = c + 1 if v else 0
        out.append(c)
    return pd.Series(out, index=s.index)
weather["连续高湿天数"] = weather.groupby("监测点ID")["高湿标记"].apply(streak).reset_index(level=0, drop=True)

# ---------- 3. 多表合并 ----------
df = (monitor
      .merge(points, on="监测点ID", how="left")
      .merge(weather.rename(columns={"日期": "监测日期"}), on=["监测点ID", "监测日期"], how="left")
      .merge(timeinfo.rename(columns={"日期": "监测日期"}), on="监测日期", how="left"))
df["近30天消杀次数"] = df.apply(
    lambda r: ((disinfect["监测点ID"] == r["监测点ID"])
               & (disinfect["消杀日期"] < r["监测日期"])
               & (disinfect["消杀日期"] >= r["监测日期"] - pd.Timedelta(days=30))).sum(), axis=1)
df = pd.get_dummies(df, columns=["区域类型", "植被类型", "周边积水情况", "是否靠近仓库"])

features = [c for c in df.columns if c not in
            ("监测点ID", "监测日期", "是否虫害爆发", "诱捕器编号", "虫口数量", "高湿标记")]
X, y = df[features].fillna(0), df["是否虫害爆发"]

# ---------- 4. 按时序切分训练 / 验证集 ----------
cut = df["监测日期"].quantile(0.8)
tr, te = df["监测日期"] <= cut, df["监测日期"] > cut
print(f"切分点 {cut.date()}，训练 {tr.sum()} 条，验证 {(~tr).sum()} 条")

# ---------- 5. 训练 LightGBM ----------
model = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                           scale_pos_weight=(y[tr] == 0).sum() / max(1, (y[tr] == 1).sum()),
                           random_state=42)
model.fit(X[tr], y[tr])
prob = model.predict_proba(X[~tr])[:, 1]
pred = (prob >= 0.5).astype(int)
print("AUC       =", round(roc_auc_score(y[~tr], prob), 3))
print("Precision =", round(precision_score(y[~tr], pred), 3))
print("Recall    =", round(recall_score(y[~tr], pred), 3))

# ---------- 6. 特征重要性 ----------
imp = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
print("\nTop3 特征：")
print(imp.head(3))
# 业务解读：结合植保经验——高温高湿与积水环境利于虫卵孵化与白蚁/蛾类繁殖；
# 雨季月份虫口基数高；历史虫口密度反映虫源积累，是最直接的先兆指标。
