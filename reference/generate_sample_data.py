#!/usr/bin/env python3
"""Generate sample data for testing the tracker pipeline."""
import pandas as pd
import random
from datetime import datetime, timedelta

random.seed(42)

jobs = [
    {"title": "Senior Data Scientist", "company": "Lululemon", "location": "Vancouver, BC", "min_amount": 130000, "max_amount": 170000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1001", "description": "machine learning python sql tensorflow a/b testing causal inference statistical modeling time series deep learning pandas numpy scikit-learn recommendation system segmentation stakeholder communication cross-functional 5+ years of experience master's computer science statistics"},
    {"title": "Data Scientist, Product Analytics", "company": "Hootsuite", "location": "Vancouver, BC", "min_amount": 110000, "max_amount": 145000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1002", "description": "python sql a/b testing hypothesis testing regression clustering machine learning product analytics segmentation kpi metrics pandas scikit-learn tableau stakeholder communication 3+ years experience master statistics"},
    {"title": "Machine Learning Engineer", "company": "Amazon", "location": "Vancouver, BC", "min_amount": 150000, "max_amount": 210000, "interval": "yearly", "job_url": "https://amazon.jobs/1003", "description": "machine learning deep learning python pytorch tensorflow nlp aws sagemaker docker kubernetes ci/cd data pipeline reinforcement learning 5+ years experience master computer science"},
    {"title": "AI/ML Consultant", "company": "Deloitte", "location": "Vancouver, BC", "min_amount": 95000, "max_amount": 140000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1004", "description": "machine learning ai consulting python sql stakeholder project management nlp rag generative ai llm strategy cross-functional communication 5+ years experience"},
    {"title": "Data Scientist", "company": "TELUS", "location": "Vancouver, BC", "min_amount": 95000, "max_amount": 130000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1005", "description": "python sql r machine learning statistical modeling regression time series a/b testing data visualization pandas scikit-learn communication stakeholder 3+ years experience bachelor statistics mathematics"},
    {"title": "Senior Product Analyst", "company": "Clio", "location": "Vancouver, BC", "min_amount": 105000, "max_amount": 135000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1006", "description": "sql python product analytics a/b testing hypothesis testing segmentation funnel analysis cohort analysis retention churn ltv metrics kpi tableau looker stakeholder cross-functional 4+ years experience"},
    {"title": "Data Analyst", "company": "BC Hydro", "location": "Vancouver, BC", "min_amount": 80000, "max_amount": 100000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1007", "description": "sql python data analysis data visualization tableau power bi excel statistical analysis regression hypothesis testing stakeholder communication 2+ years experience bachelor statistics"},
    {"title": "Applied Scientist", "company": "Microsoft", "location": "Vancouver, BC", "min_amount": 140000, "max_amount": 195000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1008", "description": "machine learning deep learning nlp python pytorch tensorflow research statistical modeling neural network transformer bert gpt recommendation system 5+ years experience phd computer science"},
    {"title": "Data Scientist - Cybersecurity", "company": "Fortinet", "location": "Burnaby, BC", "min_amount": 110000, "max_amount": 150000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1009", "description": "cybersecurity machine learning python anomaly detection classification deep learning data pipeline sql network security threat detection 3+ years experience bachelor computer science"},
    {"title": "Quantitative Analyst", "company": "RBC", "location": "Vancouver, BC", "min_amount": 100000, "max_amount": 140000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1010", "description": "python r sql statistical modeling time series regression machine learning quantitative analysis risk modeling financial data pandas numpy 5+ years experience master mathematics statistics"},
    {"title": "Data Engineer", "company": "Shopify", "location": "Vancouver, BC (Remote)", "min_amount": 120000, "max_amount": 165000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1011", "description": "python sql spark pyspark airflow dbt snowflake data pipeline etl data warehouse docker kubernetes aws gcp 4+ years experience"},
    {"title": "Business Intelligence Analyst", "company": "Bench Accounting", "location": "Vancouver, BC", "min_amount": 75000, "max_amount": 95000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1012", "description": "sql tableau power bi excel data analysis data visualization metrics kpi reporting stakeholder communication 2+ years experience"},
    {"title": "NLP Engineer", "company": "Cohere", "location": "Vancouver, BC (Remote)", "min_amount": 140000, "max_amount": 190000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1013", "description": "nlp natural language processing python pytorch transformer bert gpt llm machine learning deep learning rag langchain 4+ years experience master computer science"},
    {"title": "Data Scientist", "company": "Vancouver Coastal Health", "location": "Vancouver, BC", "min_amount": 85000, "max_amount": 110000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1014", "description": "python r sql statistical analysis data visualization machine learning regression healthcare data pandas hypothesis testing 3+ years experience bachelor statistics"},
    {"title": "Growth Analyst", "company": "Later (Mavrck)", "location": "Vancouver, BC", "min_amount": 80000, "max_amount": 100000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1015", "description": "sql python product analytics a/b testing segmentation funnel analysis ltv churn retention metrics kpi looker 2+ years experience"},
    {"title": "Senior ML Engineer", "company": "D-Wave Systems", "location": "Burnaby, BC", "min_amount": 130000, "max_amount": 170000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1016", "description": "machine learning deep learning python pytorch tensorflow quantum computing optimization algorithm docker aws 5+ years experience master computer science"},
    {"title": "AI Strategy Consultant", "company": "Accenture", "location": "Vancouver, BC", "min_amount": 100000, "max_amount": 145000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1017", "description": "ai machine learning consulting strategy stakeholder llm generative ai rag project management cross-functional python sql communication 5+ years experience"},
    {"title": "Data Analyst, Marketing", "company": "Thinkific", "location": "Vancouver, BC", "min_amount": 70000, "max_amount": 90000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1018", "description": "sql python data analysis a/b testing segmentation marketing analytics funnel analysis metrics kpi google analytics excel 2+ years experience"},
    {"title": "Security Data Analyst", "company": "Absolute Software", "location": "Vancouver, BC", "min_amount": 90000, "max_amount": 120000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1019", "description": "cybersecurity data analysis python sql anomaly detection machine learning siem security analytics threat intelligence statistical analysis 3+ years experience"},
    {"title": "Research Scientist", "company": "Borealis AI (RBC)", "location": "Vancouver, BC", "min_amount": 120000, "max_amount": 160000, "interval": "yearly", "job_url": "https://linkedin.com/jobs/1020", "description": "machine learning deep learning nlp reinforcement learning python pytorch research neural network statistical modeling 4+ years experience phd mathematics computer science"},
]

df = pd.DataFrame(jobs)
df["scraped_date"] = datetime.now().strftime("%Y-%m-%d")
df["search_query"] = [random.choice(["data scientist", "ML engineer", "AI consultant", "product analyst", "data analyst"]) for _ in range(len(df))]
df["application_status"] = "New"
df["notes"] = ""
df["noc_code_guess"] = ""
df["bcpnp_tech_eligible"] = ""

# Assign NOC codes
title_noc = {
    "data scientist": "21211 (Data Scientists)",
    "machine learning": "21211 (Data Scientists)",
    "ml engineer": "21211 (Data Scientists)",
    "applied scientist": "21211 (Data Scientists)",
    "research scientist": "21211 (Data Scientists)",
    "nlp engineer": "21211 (Data Scientists)",
    "quantitative analyst": "21211 (Data Scientists)",
    "cybersecurity": "21220 (Cybersecurity Specialists)",
    "security": "21220 (Cybersecurity Specialists)",
    "ai consultant": "21221 (Business Systems Specialists)",
    "ai strategy": "21221 (Business Systems Specialists)",
    "product analyst": "21221 (Business Systems Specialists)",
    "growth analyst": "21221 (Business Systems Specialists)",
    "data analyst": "21223 (Database Analysts)",
    "business intelligence": "21223 (Database Analysts)",
    "data engineer": "21231 (Software Engineers)",
}

bcpnp_nocs = {"21211", "21220", "21221", "21223", "21231"}

for idx, row in df.iterrows():
    t = row["title"].lower()
    for keyword, noc in title_noc.items():
        if keyword in t:
            df.at[idx, "noc_code_guess"] = noc
            noc_code = noc.split(" ")[0]
            df.at[idx, "bcpnp_tech_eligible"] = "✅ Yes" if noc_code in bcpnp_nocs else "❓ Check"
            break

df.to_csv("/home/claude/job-toolkit/data/sample_jobs_raw.csv", index=False)
print(f"✅ Generated {len(df)} sample jobs → data/sample_jobs_raw.csv")
