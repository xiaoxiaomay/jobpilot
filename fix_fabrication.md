# Fix Request: Eliminate AI Fabrication in Resume & Cover Letter Generation

## Problem

The current `core/resume_generator.py` generates resumes and cover letters that contain:
1. **Fabricated metrics** — e.g., "achieving 95% accuracy", "reduced fraudulent activities by 40%" — these numbers don't exist in the user's profile
2. **Fabricated work descriptions** — e.g., bullet points that describe tasks the user never actually did, or reframe their experience in misleading ways
3. **Embellished claims** — e.g., attributing results to the user that were team accomplishments, or describing technologies they didn't personally use

This is a critical issue. If a hiring manager asks about these claims in an interview, the user cannot back them up. It also creates legal risk for immigration applications where employment details must be verifiable.

## Required Changes

### 1. Update the Claude API prompt in `core/resume_generator.py`

Add the following rules to the system prompt or user prompt that gets sent to the Claude API:

```
CRITICAL RULES — DO NOT VIOLATE:

1. NEVER FABRICATE NUMBERS: Do not invent any metrics, percentages, dollar amounts, 
   time savings, accuracy scores, or quantified results. Only use numbers that 
   appear EXACTLY in the candidate profile below. If a bullet point in the profile 
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
```

### 2. Add a post-generation validation step

After the Claude API returns generated content, add a validation function that:

```python
def validate_no_fabrication(generated_content: dict, profile: dict) -> dict:
    """
    Check generated resume/cover letter for potential fabrications.
    
    Returns:
        dict with 'warnings' list of suspicious claims found
    """
    # Known real numbers from the profile
    ALLOWED_NUMBERS = {
        "5%", "30%", "0.2%", "0.5%", "2.5x", "2.5X",
        "13 million", "$13", "31 million", "$31", "22 million", "$22",
        "100+", "9 entities", "20+", "22 entities", "18 countries", 
        "7,000", "7000", "10+", "10 years",
    }
    
    warnings = []
    
    # Check all text content for percentage patterns not in allowed list
    import re
    all_text = str(generated_content)
    
    # Find all percentage mentions
    percentages = re.findall(r'\d+\.?\d*%', all_text)
    for pct in percentages:
        if pct not in ALLOWED_NUMBERS:
            warnings.append(f"⚠️ Possibly fabricated metric: {pct}")
    
    # Find all dollar amounts
    dollars = re.findall(r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|k|M|B))?', all_text)
    for d in dollars:
        if not any(allowed in d for allowed in ALLOWED_NUMBERS):
            warnings.append(f"⚠️ Possibly fabricated dollar amount: {d}")
    
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
                warnings.append(f"⚠️ Possibly fabricated claim: '{m}'")
    
    return {"warnings": warnings}
```

### 3. Show warnings in the Streamlit Apply page

In `pages/2_📝_Apply.py`, after generating the resume, display any warnings:

```python
# After generation
validation = validate_no_fabrication(generated_content, profile)
if validation["warnings"]:
    st.warning("⚠️ Review these potentially fabricated claims before submitting:")
    for w in validation["warnings"]:
        st.write(w)
    st.info("Please verify all numbers and claims match your real experience.")
```

### 4. Update the resume preview to highlight unverified claims

If possible, in the resume preview section, highlight any bullet points that contain 
numbers NOT in the ALLOWED_NUMBERS set, so the user can quickly spot them for review.

## Testing

After making these changes, test by:
1. Generate a resume for the Fortinet Data Scientist - Cybersecurity position
2. Verify NO fabricated percentages appear (like "95% accuracy" or "reduced by 40%")
3. Verify all bullet points can be traced back to master_profile.json content
4. Verify the cover letter only uses numbers from the ALLOWED_NUMBERS list
5. Verify the validation warnings appear when fabrication is detected
