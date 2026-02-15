"""
Networking Intelligence Module

Generates LinkedIn search URLs and networking recommendations
for each company in the job pool.

NOTE: This does NOT scrape LinkedIn. It generates search URLs
that the user can manually open to find connections.
"""


# Companies with known Chinese/international employee presence
HIGH_CHINESE_PRESENCE = [
    "amazon", "microsoft", "google", "meta", "apple", "shopify",
    "huawei", "tencent", "alibaba", "bytedance",
    "rbc", "td", "bmo", "deloitte", "pwc", "ey", "kpmg",
    "sap", "visier", "d-wave", "hootsuite",
]

MEDIUM_PRESENCE = [
    "telus", "fortinet", "absolute", "bench", "clio",
]


def generate_networking_intel(company: str, location: str = "Vancouver") -> dict:
    """
    Generate LinkedIn search URLs and networking recommendations.

    Returns dict with:
    - search_urls: list of LinkedIn search URL dicts
    - networking_tips: list of suggested actions
    - networking_score: networking bonus (0-15)
    """
    company_clean = company.strip()
    company_encoded = company_clean.replace(" ", "%20")
    base = "https://www.linkedin.com/search/results/people/"

    searches = [
        {
            "label": f"🎓 北大校友 at {company_clean}",
            "url": f"{base}?keywords=peking%20university&currentCompany=%5B%22{company_encoded}%22%5D",
            "why": "PKU alumni are most likely to respond to your outreach",
        },
        {
            "label": f"🎓 NYIT alumni at {company_clean}",
            "url": f"{base}?keywords=NYIT&currentCompany=%5B%22{company_encoded}%22%5D",
            "why": "NYIT alumni can speak to shared educational background",
        },
        {
            "label": f"🇨🇳 Chinese DS/ML professionals at {company_clean}",
            "url": (
                f"{base}?keywords=data%20scientist%20machine%20learning"
                f"&currentCompany=%5B%22{company_encoded}%22%5D"
                f"&geoUrn=%5B%22103366113%22%5D"
            ),
            "why": "Chinese-origin professionals may understand your background and be willing to refer",
        },
        {
            "label": f"🚗 Ex-Uber at {company_clean}",
            "url": f"{base}?keywords=uber&currentCompany=%5B%22{company_encoded}%22%5D",
            "why": "Former Uber colleagues understand the pace and data culture you come from",
        },
        {
            "label": f"🏢 Ex-PwC at {company_clean}",
            "url": f"{base}?keywords=pwc&currentCompany=%5B%22{company_encoded}%22%5D",
            "why": "Former PwC consultants value the analytical rigor you bring",
        },
        {
            "label": f"📊 DS/ML team at {company_clean} Vancouver",
            "url": (
                f"{base}?keywords=data%20scientist"
                f"&currentCompany=%5B%22{company_encoded}%22%5D"
                f"&geoUrn=%5B%22103366113%22%5D"
            ),
            "why": "Find potential hiring managers or team members to connect with",
        },
    ]

    tips = [
        f"1. Search for PKU/NYIT alumni at {company_clean} — they're most likely to accept your connection request",
        f"2. Look for Chinese-origin data scientists at {company_clean} — they understand the challenge of breaking into the Canadian market",
        f"3. Check if anyone in the DS team at {company_clean} previously worked at Uber or PwC — shared experience is a strong networking hook",
        f"4. When connecting, mention specific things: your PKU math background, Uber growth analytics experience, or PwC cross-border M&A work",
    ]

    company_lower = company_clean.lower()
    if any(c in company_lower for c in HIGH_CHINESE_PRESENCE):
        bonus = 10
    elif any(c in company_lower for c in MEDIUM_PRESENCE):
        bonus = 5
    else:
        bonus = 2

    return {
        "search_urls": searches,
        "networking_tips": tips,
        "networking_score": bonus,
    }


# Connection request templates
TEMPLATES = {
    "pku_alumni": (
        "Hi {name}, I noticed you're a PKU alumnus working at {company} — "
        "小校友在温哥华！I'm a PKU Math graduate (2011) with 10+ years in data science "
        "and ML (ex-Uber, ex-PwC), recently relocated to Vancouver and pursuing my "
        "M.S. in CS at NYIT. I'd love to connect and hear about your experience at "
        "{company}. Would you be open to a brief chat? Thanks!"
    ),
    "nyit_alumni": (
        "Hi {name}, I see you're an NYIT alumnus at {company} — great to find a "
        "fellow NYIT connection! I'm currently in the M.S. Computer Science program "
        "at NYIT Vancouver, with 10+ years of data science experience. I'd love to "
        "connect and learn about the data team at {company}. Thanks!"
    ),
    "ex_uber": (
        "Hi {name}, I noticed you previously worked at Uber — I was a City Lead / "
        "South China Lead at Uber from 2015-2016, working on growth analytics and "
        "marketplace optimization. Small world! I'm now in Vancouver looking for DS "
        "opportunities. Would love to connect!"
    ),
    "ex_pwc": (
        "Hi {name}, I see you have PwC in your background — I was a Senior Consultant "
        "at PwC Management Consulting (2011-2015), specializing in M&A and growth "
        "strategy. I'm now in Vancouver transitioning into data science. Would love "
        "to connect with a fellow PwC alum!"
    ),
    "chinese_professional": (
        "Hi {name}, I'm a data scientist based in Vancouver with 10+ years of "
        "experience in ML/AI (ex-Uber, ex-PwC, Peking University). I'm exploring "
        "opportunities in {company}'s data team and would love to connect and learn "
        "about your experience there. Thanks!"
    ),
    "hiring_manager": (
        "Hi {name}, I saw the {job_title} opening at {company} and was very excited "
        "about it. I have 10+ years of ML/AI experience including scaling Uber China's "
        "analytics (5%→30% market share) and deploying GNN-based systems at a "
        "Sequoia-backed startup. I've applied through the portal and would welcome "
        "the chance to briefly discuss how my background aligns. Would you be open "
        "to a quick chat?"
    ),
}
