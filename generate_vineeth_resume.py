#!/usr/bin/env python3
"""
Generate Modern HTML and PDF Resume for Vineeth Prathapachandra Kaimal.
Updated:
- Use formal executive portrait photo: vineeth_2025_formal_pic.jpg
"""

import os
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKSPACE_DIR = Path(r"C:\Users\vinee\vineeth_jobs")
RESUME_DIR = WORKSPACE_DIR / "Resume"
PHOTO_PATH = RESUME_DIR / "vineeth_2025_formal_pic.jpg"
HTML_OUTPUT_PATH = RESUME_DIR / "Vineeth_Technical_Leader.html"
PDF_OUTPUT_PATH = RESUME_DIR / "Vineeth_Technical_Leader.pdf"

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
        raise FileNotFoundError(f"Photo not found at {photo_path}")
    with open(photo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded_string}"

def generate_html(photo_b64: str) -> str:
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vineeth Prathapachandra Kaimal - Resume</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=Open+Sans:wght@400;500;600;700&display=swap');

        @page {{
            size: A4 portrait;
            margin: 0;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Open Sans', system-ui, -apple-system, sans-serif;
            background-color: #ffffff;
            color: #2d3748;
            font-size: 9.3pt;
            line-height: 1.4;
            -webkit-font-smoothing: antialiased;
        }}

        .page {{
            width: 210mm;
            height: 297mm;
            margin: 0 auto;
            background: #ffffff;
            display: flex;
            overflow: hidden;
        }}

        /* ── LEFT COLUMN (MAIN CONTENT) ── */
        .left-column {{
            width: 63%;
            height: 100%;
            padding: 14mm 12mm 12mm 15mm;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        /* Header */
        .header {{
            margin-bottom: 4px;
        }}

        .first-name {{
            font-family: 'Montserrat', sans-serif;
            font-size: 25pt;
            font-weight: 500;
            color: #8c7373;
            letter-spacing: 3.5px;
            text-transform: uppercase;
            line-height: 1.05;
        }}

        .last-name {{
            font-family: 'Montserrat', sans-serif;
            font-size: 28pt;
            font-weight: 800;
            color: #1a1c38;
            letter-spacing: 3px;
            text-transform: uppercase;
            line-height: 1.1;
            margin-bottom: 6px;
        }}

        .job-title-tag {{
            font-family: 'Montserrat', sans-serif;
            font-size: 10.5pt;
            font-weight: 600;
            color: #1a1c38;
            margin-bottom: 3px;
        }}

        .company-highlights {{
            font-size: 9.2pt;
            font-weight: 600;
            color: #718096;
        }}

        .divider {{
            height: 1px;
            background-color: #333333;
            margin: 12px 0 14px 0;
            opacity: 0.75;
        }}

        /* Section Headings */
        .section-title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 11pt;
            font-weight: 800;
            color: #1a1c38;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}

        .section {{
            margin-bottom: 10px;
        }}

        .summary-text {{
            font-size: 9pt;
            color: #334155;
            text-align: justify;
            line-height: 1.42;
        }}

        /* Experience List */
        .experience-container {{
            display: flex;
            flex-direction: column;
            gap: 13px;
        }}

        .job-item {{
            display: flex;
            flex-direction: column;
        }}

        .job-header-row {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 2px;
        }}

        .job-role {{
            font-family: 'Montserrat', sans-serif;
            font-size: 9.5pt;
            font-weight: 800;
            color: #1a1c38;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}

        .job-dates {{
            font-family: 'Open Sans', sans-serif;
            font-size: 8.8pt;
            font-weight: 600;
            color: #4a5568;
            white-space: nowrap;
        }}

        .job-company {{
            font-size: 8.8pt;
            font-weight: 600;
            color: #4a5568;
            margin-bottom: 4px;
        }}

        .job-bullets {{
            list-style: none;
            padding-left: 0;
        }}

        .job-bullets li {{
            position: relative;
            padding-left: 12px;
            margin-bottom: 3.5px;
            font-size: 8.8pt;
            color: #334155;
            line-height: 1.38;
        }}

        .job-bullets li:last-child {{
            margin-bottom: 0;
        }}

        .job-bullets li::before {{
            content: "•";
            position: absolute;
            left: 1px;
            top: -1px;
            color: #8c7373;
            font-size: 9.5pt;
        }}


        /* ── RIGHT COLUMN (SIDEBAR) ── */
        .sidebar {{
            width: 37%;
            height: 100%;
            background-color: #8c7373;
            display: flex;
            flex-direction: column;
            color: #ffffff;
        }}

        .photo-block {{
            width: 100%;
            height: 240px;
            background-color: #8c7373;
            overflow: hidden;
            flex-shrink: 0;
            padding: 0;
            border-bottom: 0.3px solid #ffffff;
            box-sizing: border-box;
        }}

        .photo-block img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center top;
            display: block;
        }}

        .sidebar-content {{
            padding: 14px 14px 14px 16px;
            display: flex;
            flex-direction: column;
            gap: 11px;
            flex-grow: 1;
        }}

        .sidebar-title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 10.5pt;
            font-weight: 800;
            color: #1a1c38;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}

        .sidebar-divider {{
            height: 1px;
            background-color: rgba(26, 28, 56, 0.3);
            margin: 1px 0 0 0;
        }}

        /* Contact Items */
        .contact-list {{
            display: flex;
            flex-direction: column;
            gap: 7.5px;
        }}

        .contact-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 8.2pt;
            color: #ffffff;
            font-weight: 500;
        }}

        .icon-badge {{
            width: 22px;
            height: 22px;
            background-color: #ffffff;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}

        .icon-badge svg {{
            width: 11px;
            height: 11px;
            stroke: #1a1c38;
            fill: none;
        }}

        .contact-item a {{
            color: #ffffff;
            text-decoration: none;
            word-break: break-all;
        }}

        /* Education Items */
        .edu-list {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .edu-item {{
            display: flex;
            flex-direction: column;
        }}

        .edu-degree {{
            font-family: 'Montserrat', sans-serif;
            font-size: 8.6pt;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.25;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}

        .edu-year {{
            font-size: 8pt;
            color: #f1eaea;
            margin: 1.5px 0 0.5px 0;
            font-weight: 600;
        }}

        .edu-school {{
            font-size: 8.2pt;
            color: #ffffff;
            opacity: 0.95;
        }}

        /* Highlights / Extra-Curricular in Sidebar */
        .achievements-list {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .achievement-item {{
            display: flex;
            flex-direction: column;
        }}

        .achievement-title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 8.3pt;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.25;
        }}

        .achievement-sub {{
            font-size: 7.9pt;
            color: #f1eaea;
            opacity: 0.95;
        }}

        /* Styled Skills & Badges in Sidebar */
        .skills-list {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .skill-group {{
            display: flex;
            flex-direction: column;
        }}

        .skill-group-name {{
            font-family: 'Montserrat', sans-serif;
            font-size: 8pt;
            font-weight: 700;
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-bottom: 4px;
            border-bottom: 1px solid rgba(255,255,255,0.25);
            padding-bottom: 2px;
        }}

        .badge-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }}

        .badge-tag {{
            background: rgba(26, 28, 56, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.35);
            border-radius: 4px;
            padding: 3px 6.5px;
            font-size: 7.8pt;
            font-weight: 600;
            color: #ffffff;
            letter-spacing: 0.1px;
            white-space: nowrap;
        }}

        /* Key Tools Badges */
        .tools-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 4.5px;
        }}

        .tool-badge {{
            background: rgba(26, 28, 56, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.4);
            border-radius: 4px;
            padding: 3.5px 7.5px;
            font-size: 8pt;
            font-weight: 600;
            color: #ffffff;
            letter-spacing: 0.2px;
            white-space: nowrap;
        }}
    </style>
</head>
<body>
    <div class="page">
        <!-- ── MAIN LEFT COLUMN ── -->
        <div class="left-column">
            <div>
                <!-- Header -->
                <header class="header">
                    <div class="first-name">Vineeth</div>
                    <div class="last-name">Kaimal</div>
                    <div class="job-title-tag">Technical Leader | Power Integrity, Thermal &amp; Packaging</div>
                    <div class="company-highlights">Nokia Finland &nbsp;|&nbsp; Ex-ANSYS &nbsp;|&nbsp; Ex-Qualcomm</div>
                </header>

                <div class="divider"></div>

                <!-- ABOUT ME -->
                <section class="section">
                    <h2 class="section-title">About Me</h2>
                    <p class="summary-text">
                        Results-driven engineering leader with 15 years of expertise in Power Integrity, Advanced Packaging, SoC PDN sign-off, and Thermal Analysis. Demonstrated success in building and directing global cross-functional teams (25+ engineers), setting technical strategy, and delivering AI-driven automation platforms that reduce silicon area, lower cost, and ensure product reliability across cutting-edge technology nodes.
                    </p>
                </section>

                <div class="divider"></div>
            </div>

            <!-- WORK EXPERIENCE -->
            <section class="section" style="margin-bottom: 0;">
                <h2 class="section-title">Work Experience</h2>

                <div class="experience-container">
                    <!-- Nokia -->
                    <div class="job-item">
                        <div class="job-header-row">
                            <span class="job-role">Technical Leader &ndash; Power Integrity</span>
                            <span class="job-dates">Dec 2022 &ndash; Present</span>
                        </div>
                        <div class="job-company">Nokia &bull; System-level PI, Advanced Packaging &amp; Thermal Leadership</div>
                        <ul class="job-bullets">
                            <li>Define and own technical strategy for system-level power integrity and package thermal sign-off across high-speed product portfolios.</li>
                            <li>Architect and lead development of AI-driven automation platforms for package ball visualization, layout modification, and ballout optimization &ndash; directly reducing design cycle time.</li>
                            <li>Drive SoC die size optimization from a PI perspective, delivering measurable silicon area and cost reduction.</li>
                            <li>Lead advanced package-level and component thermal analysis programs to proactively mitigate reliability risks.</li>
                        </ul>
                    </div>

                    <!-- Qualcomm -->
                    <div class="job-item">
                        <div class="job-header-row">
                            <span class="job-role">Staff / Lead / Senior Engineer</span>
                            <span class="job-dates">Jan 2016 &ndash; Dec 2022</span>
                        </div>
                        <div class="job-company">Qualcomm &bull; SoC &amp; Hard-Macro PDN Sign-off | Team Lead</div>
                        <ul class="job-bullets">
                            <li>Built, mentored, and directed a 25-member global engineering team delivering 6+ concurrent sign-off programs across 3lpe, 4ff, 5lpe, and 7ff nodes.</li>
                            <li>Owned end-to-end SoC PDN sign-off strategy; drove early floorplan architecture, padring layout, bump planning, and ESD placement decisions.</li>
                            <li>Engineered 200+ automation scripts (Perl/Tcl) and an automated HTML reporting system, unifying sign-off visibility across all hard macros.</li>
                            <li>Leveraged ANSYS RedHawk, RedHawk-SC, and Cadence Voltus for static/dynamic IR drop, signal EM, and ESD clamp-to-instance validation.</li>
                        </ul>
                    </div>

                    <!-- INVECAS -->
                    <div class="job-item">
                        <div class="job-header-row">
                            <span class="job-role">Senior Engineer</span>
                            <span class="job-dates">Aug 2015 &ndash; Jan 2016</span>
                        </div>
                        <div class="job-company">INVECAS (via Soctronics) &bull; CAD and Methodology Team</div>
                        <ul class="job-bullets">
                            <li>Established internal CAD methodologies and automated PI validation sign-off flows adopted across active production projects.</li>
                        </ul>
                    </div>

                    <!-- ANSYS Apache -->
                    <div class="job-item">
                        <div class="job-header-row">
                            <span class="job-role">Applications Engineer</span>
                            <span class="job-dates">Aug 2011 &ndash; Aug 2015</span>
                        </div>
                        <div class="job-company">ANSYS Apache &bull; Technical Interface for Tier-1 Accounts</div>
                        <ul class="job-bullets">
                            <li>Served as primary engineering interface for Tier-1 accounts including Qualcomm, Atheros, and STMicroelectronics; led flow development, foundry validation, and platform adoption.</li>
                            <li>Delivered technical workshops and custom feature prototyping for RedHawk and Totem platforms.</li>
                        </ul>
                    </div>
                </div>
            </section>
        </div>

        <!-- ── RIGHT SIDEBAR ── -->
        <div class="sidebar">
            <!-- Full Width Photo -->
            <div class="photo-block">
                <img src="{photo_b64}" alt="Vineeth Prathapachandra Kaimal">
            </div>

            <div class="sidebar-content">
                <!-- CONTACTS -->
                <div>
                    <h3 class="sidebar-title">Contacts</h3>
                    <div class="contact-list">
                        <div class="contact-item">
                            <div class="icon-badge">
                                <svg viewBox="0 0 24 24" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
                            </div>
                            <span>+358 405490885</span>
                        </div>
                        <div class="contact-item">
                            <div class="icon-badge">
                                <svg viewBox="0 0 24 24" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
                            </div>
                            <a href="mailto:vineethkaimal1989@gmail.com">vineethkaimal1989@gmail.com</a>
                        </div>
                        <div class="contact-item">
                            <div class="icon-badge">
                                <svg viewBox="0 0 24 24" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                            </div>
                            <span>Oulu, Finland</span>
                        </div>
                        <div class="contact-item">
                            <div class="icon-badge">
                                <svg viewBox="0 0 24 24" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path><rect x="2" y="9" width="4" height="12"></rect><circle cx="4" cy="4" r="2"></circle></svg>
                            </div>
                            <a href="https://www.linkedin.com/in/vineeth-kaimal-373707a8/" target="_blank">linkedin.com/in/vineeth-kaimal-373707a8</a>
                        </div>
                    </div>
                </div>

                <div class="sidebar-divider"></div>

                <!-- EDUCATION -->
                <div>
                    <h3 class="sidebar-title">Education</h3>
                    <div class="edu-list">
                        <div class="edu-item">
                            <div class="edu-degree">B.E. (Hons) Electrical &amp; Electronics</div>
                            <div class="edu-year">2007 &ndash; 2011</div>
                            <div class="edu-school">BITS Pilani, K.K. Birla Goa Campus</div>
                        </div>
                        <div class="edu-item">
                            <div class="edu-degree">Higher Secondary (+2)</div>
                            <div class="edu-year">2007 &nbsp;|&nbsp; Score: 600/600 (100%){MEDAL_SVG}</div>
                            <div class="edu-school">H.S.E, Kerala</div>
                        </div>
                    </div>
                </div>

                <div class="sidebar-divider"></div>

                <!-- EXTRA-CURRICULAR ACHIEVEMENTS -->
                <div>
                    <h3 class="sidebar-title">Achievements</h3>
                    <div class="achievements-list">
                        <div class="achievement-item">
                            <div class="achievement-title">5x Kerala State Chess Champion</div>
                            <div class="achievement-sub">Represented Kerala in Nationals 15x &bull; FIDE ELO 2014</div>
                        </div>
                        <div class="achievement-item">
                            <div class="achievement-title">Elected Mess Secretary</div>
                            <div class="achievement-sub">BITS Pilani Goa Campus &bull; 2009 &ndash; 2010</div>
                        </div>
                    </div>
                </div>

                <div class="sidebar-divider"></div>

                <!-- SKILLS & EXPERTISE -->
                <div>
                    <h3 class="sidebar-title">Skills &amp; Expertise</h3>
                    <div class="skills-list">
                        <div class="skill-group">
                            <div class="skill-group-name">Leadership</div>
                            <div class="badge-grid">
                                <span class="badge-tag">Global Team Direction (25+)</span>
                                <span class="badge-tag">Technical Strategy</span>
                                <span class="badge-tag">Stakeholder Management</span>
                            </div>
                        </div>
                        <div class="skill-group">
                            <div class="skill-group-name">Engineering Domains</div>
                            <div class="badge-grid">
                                <span class="badge-tag">Power Integrity (PI)</span>
                                <span class="badge-tag">Package Thermal</span>
                                <span class="badge-tag">SoC PDN Sign-off</span>
                                <span class="badge-tag">IR Drop / EM / ESD</span>
                                <span class="badge-tag">CAD Methodology</span>
                            </div>
                        </div>
                        <div class="skill-group">
                            <div class="skill-group-name">Automation &amp; Scripting</div>
                            <div class="badge-grid">
                                <span class="badge-tag">Python</span>
                                <span class="badge-tag">Perl</span>
                                <span class="badge-tag">Tcl</span>
                                <span class="badge-tag">Shell Scripting</span>
                                <span class="badge-tag">HTML &amp; CSS</span>
                                <span class="badge-tag">JavaScript / jQuery</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="sidebar-divider"></div>

                <!-- KEY TOOLS -->
                <div>
                    <h3 class="sidebar-title">Key Tools</h3>
                    <div class="tools-grid">
                        <span class="tool-badge">Redhawk</span>
                        <span class="tool-badge">Redhawk-SC</span>
                        <span class="tool-badge">Redhawk-SC Electrothermal</span>
                        <span class="tool-badge">Totem</span>
                        <span class="tool-badge">System PI</span>
                        <span class="tool-badge">Voltus</span>
                        <span class="tool-badge">Power Artist</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html_content

def convert_html_to_pdf(html_path: Path, pdf_path: Path):
    print(f"Converting HTML to PDF via Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
        )
        browser.close()
    print(f"Successfully generated PDF at: {pdf_path}")

def main():
    print("Generating base64 image...")
    photo_b64 = get_base64_photo(PHOTO_PATH)
    
    print(f"Generating HTML resume at {HTML_OUTPUT_PATH}...")
    html_content = generate_html(photo_b64)
    
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Successfully saved HTML resume.")

    convert_html_to_pdf(HTML_OUTPUT_PATH, PDF_OUTPUT_PATH)

if __name__ == "__main__":
    main()
