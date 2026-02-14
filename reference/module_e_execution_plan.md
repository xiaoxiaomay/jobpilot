# 📋 Module E — 10-Week Execution Plan

## 总览

| 周 | LinkedIn任务 | GitHub项目 | 预期效果 |
|----|-------------|-----------|---------|
| W1 | 更新全部LinkedIn（headline, about, experience, skills） | 创建GitHub account + Profile README | 基础在线形象到位 |
| W2 | 发第一篇帖子 + 发10个connection requests | Project 2: retail-analytics-dashboard (SQL + dbt) | 开始建立网络 |
| W3 | 发A/B testing技术帖 + 评论5个行业帖 | Project 2: (Tableau dashboard + notebooks) | 简历可以加上Tableau/dbt |
| W4 | 分享Project 2到LinkedIn + 发connection requests | Project 1: vancouver-housing-ml (数据收集+EDA) | 第一个完整项目上线 |
| W5 | 发Vancouver data scene观察帖 + 互动 | Project 1: (建模+SHAP+Streamlit) | 本地属性建立 |
| W6 | 分享Project 1 + 写"Deploying ML on AWS"帖 | Project 1: (AWS SageMaker部署) | 简历可以加上AWS |
| W7 | 参加一个meetup/event + 发networking follow-up | Project 3: rag-research-assistant (MVP) | 扩展真实人脉 |
| W8 | 发RAG/GenAI技术帖 + 分享Project 3 | Project 4: cybersecurity-anomaly-detection | AI Consultant赛道覆盖 |
| W9 | 申请LinkedIn Community Top Voice badge | Project 4: (完成+SHAP分析) | 独特差异化定位 |
| W10 | 发总结帖"My Journey from Consulting to DS" | Project 5: quant-factor-research (整理已有经验) | 全部5个项目上线 |

---

## 每周详细任务清单

### Week 1: Foundation 🏗️

**LinkedIn (2-3小时)**
- [ ] 更新Headline（从linkedin_guide.md选一个）
- [ ] 写About section（从linkedin_guide.md复制粘贴）
- [ ] 更新所有5段Experience的描述
- [ ] 添加40个Skills（按优先级排序）
- [ ] 更新Education section
- [ ] 上传professional headshot
- [ ] 设置Location为"Vancouver, BC" + "Open to work"（仅对recruiters可见）
- [ ] 打开"Open to opportunities" → 选Data Scientist, ML Engineer, AI Consultant, Data Analyst

**GitHub (1-2小时)**
- [ ] 创建GitHub account（用professional username）
- [ ] 创建同名repo → 上传 PROFILE_README.md
- [ ] 设置profile bio
- [ ] 创建5个空repo（占位，名字先定好）

**验证**
- [ ] 让一个朋友搜"data scientist Vancouver"看你LinkedIn排第几
- [ ] 确认GitHub profile显示正常

---

### Week 2-3: Project 2 — Retail Analytics Dashboard 📊

**Week 2**
- [ ] 下载数据集（推荐：Brazilian E-Commerce Olist dataset from Kaggle）
- [ ] 搭建PostgreSQL或注册BigQuery sandbox
- [ ] 写 `schema.sql` 建表
- [ ] 初始化dbt project
- [ ] 写 staging models (`stg_orders.sql`, `stg_customers.sql`)
- [ ] 写 mart models (`dim_customers.sql`, `fct_orders.sql`)
- [ ] 写RFM segmentation SQL

**Week 3**
- [ ] 完成 `01_eda_and_data_quality.ipynb`
- [ ] 完成 `02_customer_segmentation.ipynb` (RFM + K-Means)
- [ ] 完成 `03_cohort_retention.ipynb`
- [ ] 完成 `04_ab_test_analysis.ipynb` （用starter notebook）
- [ ] 创建Tableau Public dashboard（或Looker Studio）
- [ ] 截图放入 `dashboards/screenshots/`
- [ ] 完善README（填入真实结果数字）
- [ ] Push to GitHub
- [ ] 在LinkedIn分享project + 写帖子

**完成后你可以在简历上加的技能**：Tableau, dbt, Snowflake/BigQuery, Product Analytics, Cohort Analysis, A/B Testing (portfolio)

---

### Week 4-6: Project 1 — Vancouver Housing ML 🏠

**Week 4**
- [ ] 收集数据：City of Vancouver Open Data + TransLink GTFS
- [ ] 数据清洗和合并
- [ ] 完成 `01_data_collection.ipynb`
- [ ] 完成 `02_eda.ipynb`（温哥华房价地图可视化）

**Week 5**
- [ ] 完成 `03_feature_engineering.ipynb`（地理特征、交通特征）
- [ ] 完成 `04_modeling.ipynb`（5个模型比较）
- [ ] 完成 `05_evaluation.ipynb`（SHAP分析）
- [ ] 搭建Streamlit demo app
- [ ] MLflow experiment tracking

**Week 6**
- [ ] 写Dockerfile
- [ ] 注册AWS free tier
- [ ] 部署到SageMaker（跟着AWS官方tutorial）
- [ ] 写 `deploy_sagemaker.py`
- [ ] GitHub Actions CI pipeline
- [ ] 完善README
- [ ] Push + LinkedIn帖子

**完成后你可以在简历上加的技能**：AWS SageMaker, Docker, MLflow, MLOps, Cloud Deployment, Geospatial ML

---

### Week 7-8: Project 3 — RAG Research Assistant 🤖

- [ ] 安装LangChain + ChromaDB
- [ ] 写 document ingestion pipeline
- [ ] 实现 embedding + retrieval
- [ ] 接入Claude API或OpenAI API
- [ ] RAGAS evaluation framework
- [ ] Streamlit UI
- [ ] Docker containerization
- [ ] Push + LinkedIn帖子

**完成后你可以在简历上加的技能**：RAG, LangChain, Vector Database, LLM, GenAI

---

### Week 8-9: Project 4 — Cybersecurity Anomaly Detection 🔐

- [ ] 下载CICIDS 2017 dataset
- [ ] 网络流量EDA
- [ ] Feature engineering
- [ ] 训练 Isolation Forest, OCSVM, Autoencoder
- [ ] SHAP explainability分析
- [ ] Streamlit monitoring dashboard
- [ ] Push + LinkedIn帖子

**完成后你可以在简历上加的技能**：Cybersecurity Analytics, Anomaly Detection, Network Security ML

---

### Week 10: Project 5 — Quant Factor Research 📈

- [ ] 整理你4年的量化研究经验为开源格式
- [ ] 用Qlib搭建因子研究框架
- [ ] GNN模型demo
- [ ] 回测结果可视化
- [ ] Push + LinkedIn帖子

**完成后**：你的GitHub有5个高质量pinned projects，简历上的技能短板全部被填补。

---

## 关键指标追踪

每两周检查一次：

| 指标 | 目标 | 当前 |
|------|------|------|
| LinkedIn profile views/week | 100+ | __ |
| LinkedIn search appearances/week | 50+ | __ |
| LinkedIn connections (Vancouver DS/ML) | 200+ | __ |
| GitHub repos with README | 5 | __ |
| GitHub green squares (commits) | 每周5+ | __ |
| Recruiter inbound messages | 2+/月 | __ |
| ATS pass rate on applications | 70%+ | __ |

---

## 重要提醒

1. **不要追求完美再push** — 先push MVP，后面慢慢完善。GitHub上有commit history比什么都重要。
2. **每个project都要有截图/可视化** — Recruiter不会运行你的代码，但会看README里的图。
3. **LinkedIn帖子要写英文** — 你的目标audience是温哥华的recruiter和hiring manager。
4. **结合投递使用** — 每次用pipeline.py投简历时，在cover letter里提到你的GitHub project。
5. **Project 2最先做** — 它填补的技能（Tableau, dbt, SQL, Product Analytics）出现在90%的温哥华DS JD里。
