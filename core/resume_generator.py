"""
AI-Powered Resume & Cover Letter Generator.
Uses Claude API to generate customized resume content tailored to specific JDs.
"""

import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROFILE_PATH = os.path.join(DATA_DIR, "master_profile.json")


def load_profile(path: str = PROFILE_PATH) -> dict:
    """Load the master profile JSON."""
    with open(path, "r") as f:
        return json.load(f)


def _filter_profile(profile: dict) -> dict:
    """Filter out excluded experiences (e.g., OHSU) from the profile."""
    filtered = dict(profile)
    filtered["experiences"] = [
        exp for exp in profile["experiences"]
        if exp.get("id") != "ohsu"
    ]
    return filtered


def _build_prompt(jd_text: str, company: str, title: str, role_type: str,
                  profile: dict, extra_instructions: str = "",
                  tone: str = "standard") -> str:
    """Build the Claude API prompt for resume generation."""
    filtered_profile = _filter_profile(profile)

    # Accessible tone instructions for Tier C / junior roles
    tone_block = ""
    if tone == "accessible":
        tone_block = """
## RESUME TONE: ACCESSIBLE (for Tier C / entry-mid level roles)

Since this is a junior or mid-level role, adjust the resume to:
1. Use title "Data Scientist" or "Data Analyst" — not "Head of" or "COO" or "General Manager"
2. For past roles with senior titles (Head of Quantitative Analysis, COO, General Manager):
   - Keep the real title but EMPHASIZE the hands-on technical work, not the leadership
   - Lead with technical bullets (built models, wrote code, analyzed data)
   - De-emphasize management/strategy bullets
3. Focus on DOING rather than LEADING:
   - "Built ML pipeline using LightGBM" (good)
   - "Led the development of ML infrastructure" (too senior)
   - "Analyzed marketplace metrics using SQL and Python" (good)
   - "Formulated data-driven growth strategies" (too strategic)
4. Keep the resume to 1 page if possible (de-emphasize older/less relevant experience)
5. Put Technical Skills section BEFORE Professional Experience
6. The goal is to appear as a strong individual contributor, not a manager
"""

    prompt = f"""You are an expert resume writer specializing in Canadian tech job applications.

Given the candidate's full background profile and a target job description,
generate a tailored resume that maximizes ATS keyword match while remaining
truthful to the candidate's actual experience.

## Candidate Profile:
{json.dumps(filtered_profile, indent=2)}

## Target Job Description:
{jd_text}

## Target Role Type: {role_type}
## Company: {company}
## Job Title: {title}

## CRITICAL RULES — DO NOT VIOLATE:

1. NEVER FABRICATE NUMBERS: Do not invent any metrics, percentages, dollar amounts,
   time savings, accuracy scores, or quantified results. Only use numbers that
   appear EXACTLY in the candidate profile above. If a bullet point in the profile
   says "market share expansion from 5% to 30%", you may use that. If no number
   exists for a particular achievement, describe the impact qualitatively
   (e.g., "significantly improved" or "enhanced" — NOT "improved by 35%").

2. NEVER FABRICATE WORK DESCRIPTIONS: Every bullet point you write must be
   directly based on a bullet point in the candidate profile. You may:
   - Rephrase for clarity and conciseness
   - Reorder words to front-load JD-relevant keywords
   - Combine two related bullets into one
   You may NOT:
   - Invent new tasks the candidate didn't do
   - Claim the candidate used technologies not listed in their profile
   - Describe projects that don't exist in the profile
   - Add claims like "led a team of X" unless the profile says so

3. NEVER FABRICATE TECHNOLOGIES: Only mention tools, frameworks, and languages
   that appear in the candidate's profile (skills section OR experience bullets).
   Do not add technologies just because they appear in the JD if the candidate
   doesn't have them.

4. COVER LETTER RULES: The cover letter should:
   - Reference specific achievements FROM the profile with EXACT numbers from the profile
   - Connect the candidate's REAL experience to the job requirements
   - If the candidate lacks a specific skill the JD asks for, do NOT claim they have it.
     Instead, highlight transferable skills or related experience.
   - Never use phrases like "achieving X% accuracy" or "reducing Y by Z%"
     unless those exact figures appear in the profile.

5. WHEN IN DOUBT, BE CONSERVATIVE: It's better to have a slightly less impressive
   but truthful resume than an impressive but fabricated one. The user will be
   asked about every claim in interviews.

NUMBERS YOU MAY USE (from the profile):
- Uber: market share expansion from 5% to 30%
- Shiyibei/MetLife: sales conversion rate increase from 0.2% to 0.5% (2.5x)
- PwC/Haier-Sanyo: $13 million liabilities cleared
- PwC/Haier-Sanyo: USD 31 million pension deficit deducted from deal price
- PwC/Haier-Sanyo: USD 22 million pension fund obtained
- PwC/Haier-Sanyo: 100+ key talents retained within 6 months
- PwC/Haier-Sanyo: 9 entities, 20+ rounds of negotiation
- PwC/Workday: 22 entities in 18 countries, 7,000+ employees
- PwC recognition: "Exceptional" consultant for 2 consecutive years
- PwC: 2012 China M&A Service Award

DO NOT invent any other numbers.

## Instructions:
1. Write a professional summary (2-3 sentences) that directly addresses
   what this JD is looking for, using keywords from the JD naturally.

2. Select the 4-5 most relevant experiences from the profile. For each,
   rewrite 3-5 bullet points that:
   - Start with strong action verbs
   - Include quantified results ONLY from the NUMBERS YOU MAY USE list above
   - Naturally incorporate JD keywords (don't keyword-stuff)
   - Emphasize transferable skills relevant to this specific role

3. Emphasize the candidate's INTERNATIONAL experience as a strength:
   - Cross-border M&A (Japan, SE Asia, Australia/NZ)
   - Global system implementations (18 countries)
   - Collaboration with US HQ teams
   Do NOT fabricate Canadian experience.

4. Order the technical skills section by relevance to this JD.

5. Do NOT include the OHSU experience.

6. Do NOT include the Gaff Information Technology (GM/Founder) role unless
   it is highly relevant and space allows.

{tone_block}
{f"## Additional Instructions: {extra_instructions}" if extra_instructions else ""}

## Output Format (JSON only, no markdown code fences):
{{
  "summary": "Professional summary text (2-3 sentences)",
  "experiences": [
    {{
      "id": "experience_id_from_profile",
      "title": "Job Title",
      "company": "Company Name",
      "location": "City, Country",
      "dates": "MM/YYYY — MM/YYYY",
      "bullets": ["Bullet 1", "Bullet 2", "Bullet 3"]
    }}
  ],
  "skills": {{
    "programming": ["Python", "SQL", ...],
    "ml_frameworks": ["TensorFlow", "PyTorch", ...],
    "data_tools": ["pandas", "NumPy", ...],
    "methods": ["Machine Learning", "Deep Learning", ...],
    "soft_skills": ["Cross-functional Collaboration", ...]
  }},
  "cover_letter": {{
    "opening": "Dear Hiring Manager, ...",
    "body_paragraph_1": "...",
    "body_paragraph_2": "...",
    "body_paragraph_3": "...",
    "closing": "Sincerely, ..."
  }}
}}

IMPORTANT: Return ONLY valid JSON. No markdown, no code fences, no extra text."""

    return prompt


def _parse_response(response_text: str) -> dict:
    """Parse Claude's response into structured data."""
    # Try to extract JSON from the response
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON block in the response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Could not parse Claude's response as JSON. Response starts with: {text[:200]}")


def generate_application(
    jd_text: str,
    company: str,
    title: str,
    role_type: str = "data_scientist",
    profile: dict = None,
    extra_instructions: str = "",
    tone: str = "standard",
) -> dict:
    """
    Use Claude API to generate a customized resume + cover letter.

    Args:
        jd_text: Full job description text.
        company: Company name.
        title: Job title.
        role_type: One of data_scientist, ai_consultant, product_analyst, data_analyst.
        profile: Master profile dict (loaded from file if None).
        extra_instructions: Additional prompt instructions.
        tone: "standard" or "accessible" (for Tier C / junior roles).

    Returns:
        {
            "summary": str,
            "experiences": [{"id", "title", "company", "location", "dates", "bullets": []}],
            "skills": {"programming": [], "ml_frameworks": [], ...},
            "cover_letter": {"opening", "body_paragraph_1", ...},
        }
    """
    import anthropic

    if profile is None:
        profile = load_profile()

    prompt = _build_prompt(jd_text, company, title, role_type, profile, extra_instructions, tone)

    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    result = _parse_response(response_text)

    # Validate required fields
    if "summary" not in result:
        raise ValueError("Generated content missing 'summary' field")
    if "experiences" not in result:
        raise ValueError("Generated content missing 'experiences' field")

    return result


def validate_no_fabrication(generated_content: dict, profile: dict) -> dict:
    """
    Check generated resume/cover letter for potential fabrications.

    Scans all text for percentages, dollar amounts, and quantified claims
    that don't appear in the known set of real numbers from the profile.

    Returns:
        dict with 'warnings' list of suspicious claims found.
    """
    # Known real numbers from the profile
    ALLOWED_NUMBERS = {
        "5%", "30%", "0.2%", "0.5%", "2.5x", "2.5X",
        "13 million", "$13", "31 million", "$31", "22 million", "$22",
        "100+", "9 entities", "20+", "22 entities", "18 countries",
        "7,000", "7000", "10+", "10 years",
        # Education-related
        "2012", "2007", "2011", "2024", "2026",
    }

    warnings = []
    all_text = json.dumps(generated_content)

    # Find all percentage mentions
    percentages = re.findall(r'\d+\.?\d*%', all_text)
    for pct in percentages:
        if pct not in ALLOWED_NUMBERS:
            warnings.append(f"Possibly fabricated metric: {pct}")

    # Find all dollar amounts
    dollars = re.findall(r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|k|M|B))?', all_text)
    for d in dollars:
        if not any(allowed in d for allowed in ALLOWED_NUMBERS):
            warnings.append(f"Possibly fabricated dollar amount: {d}")

    # Find suspicious quantified claims
    suspicious_patterns = [
        r'(?:reduced|increased|improved|boosted|decreased|saved|cut)\s+(?:by\s+)?\d+',
        r'\d+x\s+(?:improvement|increase|faster|better)',
        r'(?:led|managed)\s+(?:a\s+)?team\s+of\s+\d+',
    ]
    for pattern in suspicious_patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        for m in matches:
            if not any(allowed in m for allowed in ALLOWED_NUMBERS):
                warnings.append(f"Possibly fabricated claim: '{m}'")

    return {"warnings": warnings}


def generate_resume_only(
    jd_text: str,
    company: str,
    title: str,
    role_type: str = "data_scientist",
    profile: dict = None,
) -> dict:
    """Generate just the resume content (no cover letter) for faster results."""
    return generate_application(jd_text, company, title, role_type, profile)


def get_role_types() -> dict:
    """Return available role types and their descriptions."""
    return {
        "data_scientist": "Data Scientist / ML Engineer",
        "data_analyst": "Data Analyst / BI Analyst",
        "product_analyst": "Product Analyst",
        "product_manager": "Product Manager",
        "business_analyst": "Business Analyst",
        "analytics_manager": "Analytics Manager",
        "management_consultant": "Management Consultant",
        "ai_consultant": "AI / Data Consultant",
    }
