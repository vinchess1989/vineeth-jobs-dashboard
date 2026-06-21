# Job Search Requirements — Semiconductor / VLSI / EDA

## Candidate Profile
* **Name:** Vineeth Prathapachandra Kaimal
* **Current Role:** Technical Leader - Power Integrity & Advanced Packaging
* **Years of Experience:** 15 years
* **Background:** Power Integrity (PI), Advanced Packaging, SoC PDN Sign-off, Thermal Analysis, CAD Methodology
* **Key Skills:** ANSYS RedHawk, RedHawk-SC, Totem, Cadence Voltus, Grid Prototyping System (GPS), Python, Perl, Tcl, Shell Scripting, Team Leadership

## Hard Rejections
Immediately discard a job if ANY of the following are true:
* The posting is for a non-technical role (e.g., HR, Finance, Marketing, Sales) at a semiconductor company — we only want engineering/technical positions.
* The job explicitly requires a security clearance that restricts to a specific country's citizens only (e.g., "must be a US citizen with active security clearance").

## Target Job Criteria

A job is a match if it satisfies the criteria in ALL of the following categories:

**1. Domain & Technical Area:**
Must be in at least ONE of the following technical domains, with a strong preference for the first four:
* **Power Integrity (PI) / Signal Integrity (SI):** SoC PDN sign-off, IR Drop, EM, ESD, power analysis, RedHawk/Voltus
* **Advanced Packaging / Thermal:** Package thermal analysis, IC packaging, ballout optimization
* **CAD / Methodology:** CAD tool methodology, sign-off flow automation, EDA integration
* **Physical Design:** Floor planning, padring layout, bump planning, placement & routing
* **EDA Tools:** Applications Engineer, Technical Account Manager, or EDA software engineering
* **VLSI / SoC Design:** General SoC architecture, ASIC design
* **Engineering Leadership:** CAD manager, PI/SI manager, or SoC physical design lead

**2. Location & Work Model:**
* **Yes Match (Location):** 
  * Finland, Europe (outside Finland), or UK (England, Scotland, Ireland). This is the highest priority region.
  * India or Asia (e.g., Taiwan, South Korea, Singapore).
  * Fully Remote with worldwide eligibility.
  * United States, ONLY IF the job explicitly mentions visa sponsorship or relocation.
* **Hard Rejection (Location):** 
  * Reject any US-based role that explicitly requires US residency, US Citizenship, or states "no visa sponsorship".
* **Work Model:** Look for Full-Time, but also actively flag **Part-Time, Contract, Freelance, or Gig-based** roles, especially if they are at startups or consultancies.

**3. Experience Level & Role Type:**
* **Priority Match:** Senior Leadership roles (Principal Engineer, Director, Manager, Technical Leader, Staff Engineer)
* **Company Type Match:** Highly prioritize semiconductor startups and specialized consultancies hiring for these leadership roles.
* Mark as "yes" for roles matching 10-15+ years of experience in the target domains.
* Mark as "maybe" for senior roles with slightly fewer years (e.g. 8-10) if they have a leadership title.
* Entry-level or mid-level roles (e.g. < 7 years) should be marked as "no" unless it's a rapidly growing startup.

**4. Application Deadline:**
* The last date of application MUST be in the future (use today's date for comparison)
* If the deadline has already passed, discard the job
* If no deadline is explicitly mentioned, assume it is still active

## Agent Instructions
When evaluating a job posting, you MUST use your web fetch tool to visit the URL to check the application deadline and read the full job description. Logically check if it fits the combinations defined above.

**Tracking Evaluations:** After evaluating a "pending" job in `jobs.json`, you MUST update that specific job's entry directly within `jobs.json` in-place. Set `"visited": "yes"`, update `"matches_requirements"` to `"yes"` (if it matched), `"maybe"` (if it is a maybe match), or `"no"` (if it was discarded), and set `"reason"` to a brief 1-sentence explanation of your decision. Do NOT delete any records from the file!
