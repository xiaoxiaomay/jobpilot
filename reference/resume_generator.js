#!/usr/bin/env node
/**
 * Targeted Resume Generator
 * =========================
 * Generates a customized .docx resume from master_profile.json
 * tailored to a specific job description.
 *
 * Usage:
 *   node resume_generator.js --config config.json --output resume.docx
 *
 * config.json should contain:
 *   {
 *     "target_role": "data_scientist",
 *     "company_name": "Acme Corp",
 *     "job_title": "Senior Data Scientist",
 *     "selected_bullets": [...],  // from ats_scorer
 *     "extra_skills": ["tableau", "aws"],  // skills to add from JD
 *     "summary_override": ""  // optional custom summary
 *   }
 */

const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, BorderStyle, WidthType, ShadingType, HeadingLevel,
        LevelFormat, TabStopType, TabStopPosition } = require('docx');
const fs = require('fs');
const path = require('path');

// Load master profile
const profilePath = path.join(__dirname, 'master_profile.json');
const profile = JSON.parse(fs.readFileSync(profilePath, 'utf8'));

// Load config from command line
const args = process.argv.slice(2);
let configPath = 'config.json';
let outputPath = 'resume.docx';

for (let i = 0; i < args.length; i++) {
    if (args[i] === '--config') configPath = args[i + 1];
    if (args[i] === '--output') outputPath = args[i + 1];
}

const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

// ─── Helper Functions ────────────────────────────────────────────────

function sectionHeader(text) {
    return new Paragraph({
        children: [
            new TextRun({ text: text.toUpperCase(), bold: true, font: "Calibri", size: 22, color: "2B579A" }),
        ],
        spacing: { before: 200, after: 60 },
        border: {
            bottom: { style: BorderStyle.SINGLE, size: 6, color: "2B579A", space: 2 },
        },
    });
}

function bulletPoint(text, level = 0) {
    return new Paragraph({
        numbering: { reference: "resume-bullets", level: level },
        children: [new TextRun({ text: text, font: "Calibri", size: 20 })],
        spacing: { before: 20, after: 20 },
    });
}

function experienceHeader(title, company, dates) {
    return new Paragraph({
        children: [
            new TextRun({ text: title, bold: true, font: "Calibri", size: 21 }),
            new TextRun({ text: "  |  ", font: "Calibri", size: 21, color: "666666" }),
            new TextRun({ text: company, font: "Calibri", size: 21, italics: true }),
            new TextRun({ text: `\t${dates}`, font: "Calibri", size: 20, color: "666666" }),
        ],
        tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
        spacing: { before: 120, after: 40 },
    });
}

// ─── Build Resume Content ────────────────────────────────────────────

function buildResume() {
    const targetRole = config.target_role || "data_scientist";
    const summary = config.summary_override || profile.summary_templates[targetRole];
    
    // Select experiences based on target role
    const relevantExps = selectExperiences(targetRole);
    
    // Build experience section
    const experienceContent = [];
    for (const exp of relevantExps) {
        experienceContent.push(experienceHeader(exp.title, exp.company, exp.dates));
        
        // Select bullets for this experience
        const bullets = selectBullets(exp, config.selected_keywords || []);
        for (const bullet of bullets.slice(0, 5)) { // Max 5 bullets per experience
            experienceContent.push(bulletPoint(bullet));
        }
    }
    
    // Build skills section
    const skillsContent = buildSkillsSection(config.extra_skills || []);
    
    // Build education section
    const educationContent = buildEducationSection();
    
    const doc = new Document({
        styles: {
            default: {
                document: { run: { font: "Calibri", size: 20 } },
            },
        },
        numbering: {
            config: [
                {
                    reference: "resume-bullets",
                    levels: [
                        {
                            level: 0,
                            format: LevelFormat.BULLET,
                            text: "\u2022",
                            alignment: AlignmentType.LEFT,
                            style: {
                                paragraph: { indent: { left: 360, hanging: 180 } },
                            },
                        },
                        {
                            level: 1,
                            format: LevelFormat.BULLET,
                            text: "\u25E6",
                            alignment: AlignmentType.LEFT,
                            style: {
                                paragraph: { indent: { left: 720, hanging: 180 } },
                            },
                        },
                    ],
                },
            ],
        },
        sections: [{
            properties: {
                page: {
                    size: { width: 12240, height: 15840 }, // US Letter
                    margin: { top: 720, right: 720, bottom: 720, left: 720 }, // 0.5 inch margins
                },
            },
            children: [
                // ─── Header ──────────────────────────────────────────
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [
                        new TextRun({ text: profile.personal.name, bold: true, font: "Calibri", size: 36 }),
                    ],
                    spacing: { after: 40 },
                }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [
                        new TextRun({ text: `${profile.personal.location}  |  ${profile.personal.phone}  |  ${profile.personal.email}`, font: "Calibri", size: 18, color: "555555" }),
                    ],
                    spacing: { after: 40 },
                }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [
                        new TextRun({ text: `${profile.personal.linkedin}  |  ${profile.personal.github}`, font: "Calibri", size: 18, color: "2B579A" }),
                    ],
                    spacing: { after: 100 },
                }),
                
                // ─── Summary ─────────────────────────────────────────
                sectionHeader("Professional Summary"),
                new Paragraph({
                    children: [new TextRun({ text: summary, font: "Calibri", size: 20 })],
                    spacing: { after: 80 },
                }),
                
                // ─── Skills ──────────────────────────────────────────
                sectionHeader("Technical Skills"),
                ...skillsContent,
                
                // ─── Experience ──────────────────────────────────────
                sectionHeader("Professional Experience"),
                ...experienceContent,
                
                // ─── Education ───────────────────────────────────────
                sectionHeader("Education"),
                ...educationContent,
            ],
        }],
    });
    
    return doc;
}


function selectExperiences(targetRole) {
    // Always include these, ordered by relevance
    const roleOrder = {
        "data_scientist": ["ohsu", "gaff_quant", "shiyibei", "uber", "pwc"],
        "ai_consultant": ["shiyibei", "gaff_quant", "gaff_gm", "uber", "pwc"],
        "product_analyst": ["uber", "shiyibei", "gaff_gm", "gaff_quant", "pwc"],
        "data_analyst": ["uber", "ohsu", "gaff_quant", "pwc", "shiyibei"],
    };
    
    const order = roleOrder[targetRole] || roleOrder["data_scientist"];
    const expMap = {};
    for (const exp of profile.experiences) {
        expMap[exp.id] = exp;
    }
    
    // Return top 4-5 experiences in priority order
    return order.slice(0, 5).map(id => expMap[id]).filter(Boolean);
}


function selectBullets(exp, jdKeywords) {
    const bullets = exp.bullets || {};
    const allBullets = [];
    
    for (const [key, val] of Object.entries(bullets)) {
        if (key === "keywords") continue;
        if (Array.isArray(val)) {
            allBullets.push(...val);
        }
    }
    
    if (!jdKeywords || jdKeywords.length === 0) {
        return allBullets;
    }
    
    // Score bullets by keyword match
    const scored = allBullets.map(bullet => {
        const lower = bullet.toLowerCase();
        const score = jdKeywords.filter(kw => lower.includes(kw.toLowerCase())).length;
        return { bullet, score };
    });
    
    scored.sort((a, b) => b.score - a.score);
    return scored.map(s => s.bullet);
}


function buildSkillsSection(extraSkills) {
    const sections = [];
    
    const allSkills = {
        "Programming Languages": [...profile.skills.programming],
        "ML/AI Frameworks": [...profile.skills.ml_frameworks],
        "Data & Analytics": [...profile.skills.data_analysis.slice(0, 6)],
        "ML Techniques": [...profile.skills.ml_techniques.slice(0, 8)],
        "Tools & Platforms": [...profile.skills.tools_platforms],
    };
    
    // Add extra skills from JD that we should emphasize
    if (extraSkills.length > 0) {
        // Capitalize and add to appropriate categories
        const cloudTools = ["aws", "azure", "gcp", "sagemaker"];
        const biTools = ["tableau", "power bi", "looker"];
        const dataEng = ["airflow", "dbt", "spark", "snowflake", "bigquery", "databricks"];
        
        for (const skill of extraSkills) {
            const sl = skill.toLowerCase();
            if (cloudTools.some(t => sl.includes(t))) {
                allSkills["Tools & Platforms"].push(skill);
            } else if (biTools.some(t => sl.includes(t))) {
                allSkills["Tools & Platforms"].push(skill);
            } else if (dataEng.some(t => sl.includes(t))) {
                allSkills["Tools & Platforms"].push(skill);
            } else {
                allSkills["ML Techniques"].push(skill);
            }
        }
    }
    
    for (const [category, skills] of Object.entries(allSkills)) {
        sections.push(new Paragraph({
            children: [
                new TextRun({ text: `${category}: `, bold: true, font: "Calibri", size: 20 }),
                new TextRun({ text: skills.join(", "), font: "Calibri", size: 20 }),
            ],
            spacing: { before: 20, after: 20 },
        }));
    }
    
    return sections;
}


function buildEducationSection() {
    const content = [];
    
    for (const edu of profile.education) {
        content.push(new Paragraph({
            children: [
                new TextRun({ text: edu.degree, bold: true, font: "Calibri", size: 21 }),
                new TextRun({ text: `\t${edu.dates}`, font: "Calibri", size: 20, color: "666666" }),
            ],
            tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
            spacing: { before: 60, after: 20 },
        }));
        
        const details = [edu.institution];
        if (edu.second_degree) details.push(edu.second_degree);
        if (edu.expected_graduation) details.push(`Expected graduation: ${edu.expected_graduation}`);
        
        content.push(new Paragraph({
            children: [
                new TextRun({ text: details.join("  |  "), font: "Calibri", size: 20, italics: true, color: "555555" }),
            ],
            spacing: { after: 40 },
        }));
    }
    
    return content;
}


// ─── Main ────────────────────────────────────────────────────────────

async function main() {
    const doc = buildResume();
    const buffer = await Packer.toBuffer(doc);
    fs.writeFileSync(outputPath, buffer);
    console.log(`✅ Resume generated: ${outputPath}`);
    console.log(`   Target role: ${config.target_role}`);
    console.log(`   Company: ${config.company_name || 'General'}`);
}

main().catch(err => {
    console.error("Error generating resume:", err);
    process.exit(1);
});
