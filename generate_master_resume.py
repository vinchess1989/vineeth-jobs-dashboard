#!/usr/bin/env python3
"""
Generate Multi-Page Master HTML and PDF Resume from master.json for Vineeth Prathapachandra Kaimal.
Can be used as the comprehensive base for tailoring job-specific resumes.
"""

import json
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKSPACE_DIR = Path(r"C:\Users\vinee\vineeth_jobs")
RESUME_DIR = WORKSPACE_DIR / "Resume"
MASTER_JSON_PATH = RESUME_DIR / "master.json"
PHOTO_PATH = RESUME_DIR / "vineeth_2025_formal_pic.jpg"
HTML_OUTPUT_PATH = RESUME_DIR / "Vineeth_Master_Resume.html"
PDF_OUTPUT_PATH = RESUME_DIR / "Vineeth_Master_Resume.pdf"

MEDAL_SVG = (
    '<svg width="15" height="16" viewBox="0 0 24 26" style="vertical-align: -3px; margin-left: 3px;">'
    '<defs>'
    '<linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
    '<stop offset="0%" stop-color="#fef08a"/>'
    '<stop offset="50%" stop-color="#eab308"/>'
    '<stop offset="100%" stop-color="#ca8a04"/>'
    '</linearGradient>'
    '<linearGradient id="ribbonGrad" x1="0%" y1="0%" x2="0%" y2="100%">'
    '<stop offset="0%" stop-color="#fde047"/>'
    '<stop offset="100%" stop-color="#ca8a04"/>'
    '</linearGradient>'
    '</defs>'
    '<polygon points="4,0 12,11 20,0 16,0 12,6.5 8,0" fill="url(#ribbonGrad)" stroke="#a16207" stroke-width="0.6"/>'
    '<circle cx="12" cy="10" r="1.5" fill="none" stroke="#a16207" stroke-width="1"/>'
    '<circle cx="12" cy="17.5" r="7" fill="url(#goldGrad)" stroke="#854d0e" stroke-width="1.1"/>'
    '<circle cx="12" cy="17.5" r="5.8" fill="none" stroke="#fef08a" stroke-width="0.6" stroke-dasharray="1.2 1"/>'
    '<text x="12" y="20.3" font-family="\'Montserrat\', sans-serif" font-weight="900" font-size="8.5" fill="#713f12" text-anchor="middle">1</text>'
    '</svg>'
)

def get_base64_photo(photo_path: Path) -> str:
    if not photo_path.exists():
        return ""
    with open(photo_path, "rb") as f:
        return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"

def generate_master_html(data: dict, photo_b64: str) -> str:
    c = data["candidate"]
    s = data["skills"]
    
    exp_html = ""
    for job in data["experience"]:
        bullets_li = "".join([f"<li>{b}</li>" for b in job["bullets"]])
        exp_html += f"""
        <div class="job-item">
            <div class="job-header-row">
                <span class="job-role">{job['role']}</span>
                <span class="job-dates">{job['dates']}</span>
            </div>
            <div class="job-company">{job['company']} &bull; {job['scope']}</div>
            <ul class="job-bullets">
                {bullets_li}
            </ul>
        </div>
        """

    intern_html = ""
    for intern in data.get("internships", []):
        bullets_li = "".join([f"<li>{b}</li>" for b in intern["bullets"]])
        loc_str = f" ({intern['location']})" if "location" in intern else ""
        intern_html += f"""
        <div class="job-item">
            <div class="job-header-row">
                <span class="job-role">{intern['role']}</span>
                <span class="job-dates">{intern['dates']}</span>
            </div>
            <div class="job-company">{intern['company']}{loc_str}</div>
            <ul class="job-bullets">
                {bullets_li}
            </ul>
        </div>
        """

    projects_html = ""
    for proj in data.get("projects", []):
        projects_html += f"""
        <div class="job-item">
            <div class="job-header-row">
                <span class="job-role">{proj['title']}</span>
                <span class="job-dates" style="font-size:8.2pt; color:#1d4ed8;">{proj['technology']}</span>
            </div>
            <div class="job-bullets" style="padding-left:12px; margin-top:2px;">{proj['desc']}</div>
        </div>
        """

    achievements_li = "".join([f"<li>{a}</li>" for a in data.get("achievements", [])])
    extracurricular_li = "".join([f"<li>{e}</li>" for e in data.get("extra_curricular", [])])

    edu_html = ""
    for edu in data["education"]:
        details_str = edu['details']
        if "100%" in details_str:
            details_str = details_str.replace("100%)", f"100%){MEDAL_SVG}")
        edu_html += f"""
        <div class="edu-item">
            <div class="edu-degree">{edu['degree']}</div>
            <div class="edu-year">{edu['dates']} &nbsp;|&nbsp; {details_str}</div>
            <div class="edu-school">{edu['institution']}</div>
        </div>
        """

    leadership_badges = "".join([f'<span class="badge-tag">{b}</span>' for b in s["leadership"]])
    domain_badges = "".join([f'<span class="badge-tag">{b}</span>' for b in s["engineering_domains"]])
    auto_badges = "".join([f'<span class="badge-tag">{b}</span>' for b in s["automation"]])
    tool_badges = "".join([f'<span class="tool-badge">{b}</span>' for b in s["key_tools"]])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{c['name']} - Master Resume</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=Open+Sans:wght@400;500;600;700&display=swap');
        @page {{ size: A4 portrait; margin: 0; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Open Sans', sans-serif; background: #fff; color: #2d3748; font-size: 9.3pt; line-height: 1.4; }}
        .page {{ width: 210mm; min-height: 297mm; margin: 0 auto; background: #fff; display: flex; }}
        .left-column {{ width: 63%; padding: 14mm 12mm 12mm 15mm; display: flex; flex-direction: column; }}
        .header {{ margin-bottom: 4px; }}
        .first-name {{ font-family: 'Montserrat', sans-serif; font-size: 25pt; font-weight: 500; color: #8c7373; letter-spacing: 3.5px; text-transform: uppercase; line-height: 1.05; }}
        .last-name {{ font-family: 'Montserrat', sans-serif; font-size: 28pt; font-weight: 800; color: #1a1c38; letter-spacing: 3px; text-transform: uppercase; line-height: 1.1; margin-bottom: 6px; }}
        .job-title-tag {{ font-family: 'Montserrat', sans-serif; font-size: 10.5pt; font-weight: 600; color: #1a1c38; margin-bottom: 3px; }}
        .company-highlights {{ font-size: 9.2pt; font-weight: 600; color: #718096; }}
        .divider {{ height: 1px; background: #333; margin: 12px 0 14px 0; opacity: 0.75; }}
        .section-title {{ font-family: 'Montserrat', sans-serif; font-size: 11pt; font-weight: 800; color: #1a1c38; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; margin-top: 6px; }}
        .section {{ margin-bottom: 14px; }}
        .summary-text {{ font-size: 9pt; color: #334155; text-align: justify; line-height: 1.42; }}
        .experience-container {{ display: flex; flex-direction: column; gap: 12px; }}
        .job-item {{ display: flex; flex-direction: column; margin-bottom: 4px; }}
        .job-header-row {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2px; }}
        .job-role {{ font-family: 'Montserrat', sans-serif; font-size: 9.5pt; font-weight: 800; color: #1a1c38; text-transform: uppercase; letter-spacing: 0.3px; }}
        .job-dates {{ font-size: 8.8pt; font-weight: 600; color: #4a5568; white-space: nowrap; }}
        .job-company {{ font-size: 8.8pt; font-weight: 600; color: #4a5568; margin-bottom: 4px; }}
        .job-bullets {{ list-style: none; padding-left: 0; }}
        .job-bullets li {{ position: relative; padding-left: 12px; margin-bottom: 3.5px; font-size: 8.8pt; color: #334155; line-height: 1.38; }}
        .job-bullets li::before {{ content: "•"; position: absolute; left: 1px; top: -1px; color: #8c7373; font-size: 9.5pt; }}
        
        .sidebar {{ width: 37%; min-height: 297mm; background-color: #8c7373; display: flex; flex-direction: column; color: #fff; }}
        .photo-block {{ width: 100%; height: 240px; background-color: #8c7373; overflow: hidden; flex-shrink: 0; padding: 0; border-bottom: 0.3px solid #ffffff; box-sizing: border-box; }}
        .photo-block img {{ width: 100%; height: 100%; object-fit: cover; object-position: center top; display: block; }}
        .sidebar-content {{ padding: 14px 14px 14px 16px; display: flex; flex-direction: column; gap: 11px; flex-grow: 1; }}
        .sidebar-title {{ font-family: 'Montserrat', sans-serif; font-size: 10.5pt; font-weight: 800; color: #1a1c38; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }}
        .sidebar-divider {{ height: 1px; background-color: rgba(26, 28, 56, 0.3); margin: 1px 0 0 0; }}
        .contact-list {{ display: flex; flex-direction: column; gap: 7.5px; }}
        .contact-item {{ display: flex; align-items: center; gap: 10px; font-size: 8.2pt; color: #fff; font-weight: 500; }}
        .icon-badge {{ width: 22px; height: 22px; background: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
        .icon-badge svg {{ width: 11px; height: 11px; stroke: #1a1c38; fill: none; }}
        .contact-item a {{ color: #fff; text-decoration: none; word-break: break-all; }}
        .edu-list {{ display: flex; flex-direction: column; gap: 8px; }}
        .edu-item {{ display: flex; flex-direction: column; }}
        .edu-degree {{ font-family: 'Montserrat', sans-serif; font-size: 8.6pt; font-weight: 700; color: #fff; line-height: 1.25; text-transform: uppercase; letter-spacing: 0.3px; }}
        .edu-year {{ font-size: 8pt; color: #f1eaea; margin: 1.5px 0 0.5px 0; font-weight: 600; }}
        .edu-school {{ font-size: 8.2pt; color: #fff; opacity: 0.95; }}
        .skills-list {{ display: flex; flex-direction: column; gap: 8px; }}
        .skill-group {{ display: flex; flex-direction: column; }}
        .skill-group-name {{ font-family: 'Montserrat', sans-serif; font-size: 8pt; font-weight: 700; color: #fff; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.25); padding-bottom: 2px; }}
        .badge-grid {{ display: flex; flex-wrap: wrap; gap: 4px; }}
        .badge-tag {{ background: rgba(26, 28, 56, 0.35); border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 4px; padding: 3px 6.5px; font-size: 7.8pt; font-weight: 600; color: #fff; }}
        .tools-grid {{ display: flex; flex-wrap: wrap; gap: 4.5px; }}
        .tool-badge {{ background: rgba(26, 28, 56, 0.4); border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 4px; padding: 3.5px 7.5px; font-size: 8pt; font-weight: 600; color: #fff; }}
    </style>
</head>
<body>
    <div class="page">
        <div class="left-column">
            <div>
                <header class="header">
                    <div class="first-name">{c['first_name']}</div>
                    <div class="last-name">{c['last_name']}</div>
                    <div class="job-title-tag">{c['title']}</div>
                    <div class="company-highlights">{c['tagline']}</div>
                </header>
                <div class="divider"></div>
                <section class="section">
                    <h2 class="section-title">About Me</h2>
                    <p class="summary-text">{data['summary']['default']}</p>
                </section>
                <div class="divider"></div>
            </div>

            <!-- WORK EXPERIENCE -->
            <section class="section">
                <h2 class="section-title">Professional Experience (Master List)</h2>
                <div class="experience-container">
                    {exp_html}
                </div>
            </section>

            <div class="divider"></div>

            <!-- INTERNSHIPS -->
            <section class="section">
                <h2 class="section-title">Internships</h2>
                <div class="experience-container">
                    {intern_html}
                </div>
            </section>

            <div class="divider"></div>

            <!-- ACADEMIC & TECHNICAL PROJECTS -->
            <section class="section">
                <h2 class="section-title">Engineering Projects</h2>
                <div class="experience-container">
                    {projects_html}
                </div>
            </section>

            <div class="divider"></div>

            <!-- ACHIEVEMENTS -->
            <section class="section">
                <h2 class="section-title">Honors &amp; Achievements</h2>
                <ul class="job-bullets">
                    {achievements_li}
                </ul>
            </section>

            <div class="divider"></div>

            <!-- EXTRA-CURRICULAR -->
            <section class="section">
                <h2 class="section-title">Extra-Curricular Activities &amp; Leadership</h2>
                <ul class="job-bullets">
                    {extracurricular_li}
                </ul>
            </section>
        </div>

        <!-- RIGHT SIDEBAR -->
        <div class="sidebar">
            <div class="photo-block">
                <img src="{photo_b64}" alt="{c['name']}">
            </div>
            <div class="sidebar-content">
                <div>
                    <h3 class="sidebar-title">Contacts</h3>
                    <div class="contact-list">
                        <div class="contact-item">
                            <div class="icon-badge"><svg viewBox="0 0 24 24" stroke-width="2.5"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg></div>
                            <span>{c['contact']['phone']}</span>
                        </div>
                        <div class="contact-item">
                            <div class="icon-badge"><svg viewBox="0 0 24 24" stroke-width="2.5"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg></div>
                            <a href="mailto:{c['contact']['email']}">{c['contact']['email']}</a>
                        </div>
                        <div class="contact-item">
                            <div class="icon-badge"><svg viewBox="0 0 24 24" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg></div>
                            <span>{c['contact']['location']}</span>
                        </div>
                        <div class="contact-item">
                            <div class="icon-badge"><svg viewBox="0 0 24 24" stroke-width="2.5"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path><rect x="2" y="9" width="4" height="12"></rect><circle cx="4" cy="4" r="2"></circle></svg></div>
                            <a href="{c['contact']['linkedin_url']}" target="_blank">{c['contact']['linkedin_display']}</a>
                        </div>
                    </div>
                </div>
                <div class="sidebar-divider"></div>
                <div>
                    <h3 class="sidebar-title">Education</h3>
                    <div class="edu-list">{edu_html}</div>
                </div>
                <div class="sidebar-divider"></div>
                <div>
                    <h3 class="sidebar-title">Skills &amp; Expertise</h3>
                    <div class="skills-list">
                        <div class="skill-group">
                            <div class="skill-group-name">Leadership</div>
                            <div class="badge-grid">{leadership_badges}</div>
                        </div>
                        <div class="skill-group">
                            <div class="skill-group-name">Engineering Domains</div>
                            <div class="badge-grid">{domain_badges}</div>
                        </div>
                        <div class="skill-group">
                            <div class="skill-group-name">Automation &amp; Scripting</div>
                            <div class="badge-grid">{auto_badges}</div>
                        </div>
                    </div>
                </div>
                <div class="sidebar-divider"></div>
                <div>
                    <h3 class="sidebar-title">Key Tools</h3>
                    <div class="tools-grid">{tool_badges}</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

def main():
    print("Loading master.json...")
    with open(MASTER_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    photo_b64 = get_base64_photo(PHOTO_PATH)
    html_content = generate_master_html(data, photo_b64)
    
    with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated Master HTML at: {HTML_OUTPUT_PATH}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(HTML_OUTPUT_PATH.as_uri(), wait_until="networkidle")
        page.pdf(path=str(PDF_OUTPUT_PATH), format="A4", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        browser.close()
    print(f"Generated Master PDF at: {PDF_OUTPUT_PATH}")

if __name__ == "__main__":
    main()
