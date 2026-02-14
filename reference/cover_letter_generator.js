#!/usr/bin/env node
/**
 * Targeted Cover Letter Generator
 * ================================
 * Generates a customized cover letter based on JD analysis and master profile.
 *
 * Usage:
 *   node cover_letter_generator.js --config cl_config.json --output cover_letter.docx
 */

const { Document, Packer, Paragraph, TextRun, AlignmentType,
        TabStopType, TabStopPosition } = require('docx');
const fs = require('fs');
const path = require('path');

const profilePath = path.join(__dirname, 'master_profile.json');
const profile = JSON.parse(fs.readFileSync(profilePath, 'utf8'));

const args = process.argv.slice(2);
let configPath = 'cl_config.json';
let outputPath = 'cover_letter.docx';

for (let i = 0; i < args.length; i++) {
    if (args[i] === '--config') configPath = args[i + 1];
    if (args[i] === '--output') outputPath = args[i + 1];
}

const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

// ─── Cover Letter Templates ─────────────────────────────────────────

const templates = {
    data_scientist: {
        hook: (company, title) =>
            `I am writing to express my strong interest in the ${title} position at ${company}. With over 10 years of experience developing and deploying machine learning models across finance, insurance, and healthcare domains—and a current M.S. in Computer Science (Cybersecurity) at NYIT Vancouver—I am excited to bring my expertise in end-to-end ML pipeline development and data-driven decision-making to your team.`,
        body_highlights: [
            {
                label: "ML/DL Pipeline Development",
                text: "As Head of Quantitative Analysis at Gaff Sail Private Equity, I led the development of an end-to-end ML infrastructure encompassing model development, backtesting, and deployment. I directed the deployment of advanced models including LightGBM, Graph Neural Networks, and reinforcement learning for portfolio optimization—skills directly transferable to building production ML systems."
            },
            {
                label: "Data-Driven Impact",
                text: "At Uber China, I formulated data-driven growth strategies using A/B testing, causal inference, and predictive modeling that contributed to expanding Uber's market share from 5% to 30%. I built clustering models for user segmentation, developed Random Forest models for retention prediction, and created interactive dashboards for real-time KPI monitoring."
            },
            {
                label: "Cross-Industry Experience",
                text: "My career spans multiple domains—from biomedical research at OHSU where I analyze multi-omics cancer data, to AI platform development at a Sequoia-backed startup where I deployed NLP chatbots and Heterogeneous Graph Neural Networks. This breadth gives me the ability to quickly understand new domains and deliver impactful analytical solutions."
            },
        ],
    },
    ai_consultant: {
        hook: (company, title) =>
            `I am writing to express my keen interest in the ${title} role at ${company}. With over a decade of experience at the intersection of AI technology and business strategy—including leadership roles at a Sequoia-backed AI startup and PwC Management Consulting—I bring a rare combination of technical depth in ML/NLP/RAG systems and strategic business acumen that enables me to guide organizations through AI transformation.`,
        body_highlights: [
            {
                label: "AI Platform Leadership",
                text: "As COO of Shiyibei Technology, I led the development of an AI-driven sales platform incorporating predictive modeling, NLP chatbots, and intelligent workflow automation. Our solution achieved a 2.5x improvement in sales conversion for MetLife, demonstrating my ability to translate AI capabilities into measurable business value."
            },
            {
                label: "Enterprise Consulting",
                text: "At PwC, I was recognized as an 'Exceptional' consultant across Greater China for two consecutive years, supporting Fortune 500 clients including Haier, Volkswagen, and Daimler in strategic initiatives spanning M&A, growth planning, and operational transformation. This foundation in consulting enables me to understand client needs and communicate technical solutions in business terms."
            },
            {
                label: "End-to-End Technical Expertise",
                text: "I have hands-on experience building agentic AI workflows, RAG pipelines, and NLP systems. At Gaff Sail, I deployed advanced ML/DL models including GNNs and reinforcement learning agents. This technical depth allows me to assess feasibility, design architectures, and guide engineering teams during implementation."
            },
        ],
    },
    product_analyst: {
        hook: (company, title) =>
            `I am excited to apply for the ${title} position at ${company}. With extensive experience in product analytics, experimentation design, and growth optimization—most notably at Uber China where I helped expand market share from 5% to 30%—I am passionate about using data to drive product decisions and improve user experiences.`,
        body_highlights: [
            {
                label: "Product Experimentation",
                text: "At Uber, I led experiments on pricing elasticity, dispatching algorithm optimization, and dynamic pricing strategies using causal inference and regression modeling. I designed A/B tests and applied uplift modeling for campaign targeting across the full conversion funnel, directly impacting ride completions and driver earnings."
            },
            {
                label: "User Analytics & Segmentation",
                text: "I built K-Means clustering models for user segmentation on behavioral features, developed Random Forest models for retention prediction, and created R Shiny dashboards enabling city teams to monitor KPIs and forecast supply/demand. These tools empowered cross-functional teams to make data-informed product decisions."
            },
            {
                label: "AI Product Development",
                text: "At Shiyibei, I contributed to product iteration and UX optimization of an AI-based insurance comparison tool, integrating NLP recommendation engines and dynamic pricing algorithms. I have experience working closely with product managers and engineers to define metrics, prioritize features, and measure impact."
            },
        ],
    },
    data_analyst: {
        hook: (company, title) =>
            `I am writing to express my interest in the ${title} role at ${company}. With 10+ years of experience in data analysis, statistical modeling, and business intelligence across finance, technology, and consulting, I am eager to leverage my analytical expertise to drive insights and support data-driven decision-making at your organization.`,
        body_highlights: [
            {
                label: "Data Analysis & Visualization",
                text: "At Uber China, I utilized SQL, Python, and R for in-depth marketplace analysis and hypothesis testing. I developed interactive R Shiny dashboards for city teams to monitor operational KPIs, forecast supply/demand fluctuations, and evaluate promotional effectiveness—directly supporting business decisions."
            },
            {
                label: "Statistical Modeling",
                text: "I have extensive experience in regression modeling, time series analysis (ARIMA, Exponential Smoothing), and anomaly detection. At Gaff Sail, I built quantitative models using advanced ML techniques, demonstrating my ability to work with complex datasets and extract actionable patterns."
            },
            {
                label: "Business Impact",
                text: "My consulting background at PwC equipped me with the ability to translate complex data findings into actionable business recommendations. I've supported M&A due diligence, financial modeling, and market research for Fortune 500 clients, always bridging the gap between technical analysis and strategic decision-making."
            },
        ],
    },
};

function buildCoverLetter() {
    const role = config.target_role || "data_scientist";
    const template = templates[role];
    const company = config.company_name || "[Company]";
    const title = config.job_title || "[Position]";
    const hiringManager = config.hiring_manager || "Hiring Manager";
    const date = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    
    // Additional keywords from JD to weave in
    const jdKeywords = config.jd_matched_keywords || [];
    
    const children = [
        // Date
        new Paragraph({
            children: [new TextRun({ text: date, font: "Calibri", size: 22 })],
            spacing: { after: 200 },
        }),
        
        // Greeting
        new Paragraph({
            children: [new TextRun({ text: `Dear ${hiringManager},`, font: "Calibri", size: 22 })],
            spacing: { after: 200 },
        }),
        
        // Hook paragraph
        new Paragraph({
            children: [new TextRun({ text: template.hook(company, title), font: "Calibri", size: 22 })],
            spacing: { after: 200 },
        }),
    ];
    
    // Body paragraphs with highlights
    for (const highlight of template.body_highlights) {
        children.push(new Paragraph({
            children: [
                new TextRun({ text: `${highlight.label}: `, bold: true, font: "Calibri", size: 22 }),
                new TextRun({ text: highlight.text, font: "Calibri", size: 22 }),
            ],
            spacing: { after: 200 },
        }));
    }
    
    // Closing — mention company-specific fit
    const closingText = config.company_specific_closing ||
        `I am particularly drawn to ${company}'s mission and believe my combination of technical expertise in machine learning, data analysis, and business strategy—along with my current studies in cybersecurity—positions me to make meaningful contributions to your team. I would welcome the opportunity to discuss how my experience aligns with your needs.`;
    
    children.push(new Paragraph({
        children: [new TextRun({ text: closingText, font: "Calibri", size: 22 })],
        spacing: { after: 200 },
    }));
    
    children.push(new Paragraph({
        children: [new TextRun({ text: "Thank you for your consideration. I look forward to hearing from you.", font: "Calibri", size: 22 })],
        spacing: { after: 300 },
    }));
    
    children.push(new Paragraph({
        children: [new TextRun({ text: "Sincerely,", font: "Calibri", size: 22 })],
        spacing: { after: 100 },
    }));
    
    children.push(new Paragraph({
        children: [new TextRun({ text: profile.personal.name, bold: true, font: "Calibri", size: 22 })],
    }));
    
    children.push(new Paragraph({
        children: [
            new TextRun({ text: `${profile.personal.phone}  |  ${profile.personal.email}`, font: "Calibri", size: 20, color: "555555" }),
        ],
    }));
    
    const doc = new Document({
        sections: [{
            properties: {
                page: {
                    size: { width: 12240, height: 15840 },
                    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
                },
            },
            children: children,
        }],
    });
    
    return doc;
}

async function main() {
    const doc = buildCoverLetter();
    const buffer = await Packer.toBuffer(doc);
    fs.writeFileSync(outputPath, buffer);
    console.log(`✅ Cover letter generated: ${outputPath}`);
    console.log(`   Target role: ${config.target_role}`);
    console.log(`   Company: ${config.company_name}`);
    console.log(`   Position: ${config.job_title}`);
}

main().catch(err => {
    console.error("Error:", err);
    process.exit(1);
});
