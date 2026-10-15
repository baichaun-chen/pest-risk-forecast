# 虫害监测与风险预测 · 模拟测试全套成果

数据分析建模考题的完整解答：测试数据生成、理论答卷、建模实测、三页动态网站。

**在线预览**：https://pest-risk-forecast-ztt0idexksh.qoder.zone/ （手机 / 电脑均可访问，无需登录）

## 目录结构

```
.
├── index.html               ① 理论答卷（简答 4 题 + 工程分析 3 题 + 上线监控 2 题）
├── dataset.html             ② 数据集（5 张表完整数据，红行标注虫害爆发，可导出 CSV）
├── dashboard.html           ③ 动态看板（ROC 动画 / 混淆矩阵 / 特征重要性 / 7 天预警窗口播放）
├── dist/                    网站发布目录（与上面三个 html 同内容，用于部署）
├── data/                    5 张 CSV 测试数据（每张约 150 条）
├── generate_data.py         生成测试数据
├── model_demo.py            纯标准库建模实测（本项目已跑通）
├── bonus_solution.py        加分题标准答案（需 pandas + LightGBM）
├── export_dashboard_data.py 跑模型并导出看板 JSON
├── build_dashboard.py       构建看板页
├── build_site.py            构建理论页 + 数据集页
├── make_docx.js             生成 Word 答卷（需 Node.js）
├── dashboard_template.html  看板模板
├── 参考答案.md               答案原文（build_site / make_docx 的输入）
└── 模拟测试_已完成.docx       可提交的 Word 答卷
```

## 考题背景

某园区植保服务商管理南方多地仓储基地与户外绿化林地，需要建立虫害风险预测模型，
提前预判监测点**未来 7 天**的虫害爆发风险（二分类任务），指导巡检与预防性消杀。

## 数据说明

| 表 | 行数 | 内容 |
|---|---|---|
| 监测点基础表 | 150 | 150 个监测点（仓储/林地/绿化带各 50），含植被类型、积水、近仓库 |
| 虫情监测表 | 150 | 75 个活跃点 × 2 次监测，爆发率 31%，含 5 条脏数据（3 缺失 + -15 + 99999） |
| 气象数据表 | 150 | 与虫情记录按「监测点 + 日期」严格对齐 |
| 历史消杀记录表 | 136 | 爆发后消杀、复治、高风险预防性消杀、例行消杀 |
| 时间信息表 | 150 | 150 天日期池，含月份与是否雨季标记 |

数据按真实业务逻辑生成：高温、高湿、积水、近仓库、林地 → 虫害爆发概率显著上升，
因此模型能学到有效信号，而非纯随机噪声。

## 建模实测结果（model_demo.py）

```
清洗：150 → 145 条（剔除 3 条缺失 + 2 条异常）
时序切分：训练 116 条（正例 37）/ 验证 29 条（正例 7），切分点 2025-08-24
AUC = 0.708    Precision = 0.600    Recall = 0.429
Top3 特征：靠近仓库 0.0519 · 区域_林地 0.0519 · 相对湿度 0.0325
```

> 说明：开发环境无 pandas / LightGBM，故用纯标准库（逻辑回归 + 排列重要性）复现同一流程；
> 验证集仅 29 条，指标与特征排名对小样本较敏感，全量数据训练 LightGBM 后指标会更高。

## 重新生成

```bash
python generate_data.py            # 重新生成 5 张表（改 seed 可得不同数据）
python export_dashboard_data.py    # 跑模型并导出看板数据
python build_dashboard.py          # 生成 dashboard.html
python build_site.py               # 生成 index.html + dataset.html
node make_docx.js                  # 生成 Word 答卷（需 Node.js）
```

## 环境要求

- 三个网页：纯静态、零依赖，手机与电脑浏览器均可直接打开
- Python 脚本：仅需 Python 3 标准库，无需联网
- bonus_solution.py：需 `pip install pandas lightgbm scikit-learn`
