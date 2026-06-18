# Job Search Requirements — Semiconductor / VLSI / EDA

## Candidate Profile
* **Name:** Vineeth
* **Current Role:** (To be filled by Vineeth)
* **Years of Experience:** (To be filled by Vineeth)
* **Background:** Semiconductor, VLSI Design, EDA tools, embedded systems
* **Key Skills:** (To be filled — e.g., RTL Design, Verification, DFT, Physical Design, FPGA, Embedded C/C++, SystemVerilog, UVM, Verilog, VHDL, Cadence/Synopsys tools, etc.)

## Hard Rejections
Immediately discard a job if ANY of the following are true:
* The posting is for a non-technical role (e.g., HR, Finance, Marketing, Sales) at a semiconductor company — we only want engineering/technical positions.
* The job explicitly requires a security clearance that restricts to a specific country's citizens only (e.g., "must be a US citizen with active security clearance").

## Target Job Criteria

A job is a match if it satisfies the criteria in ALL of the following categories:

**1. Domain & Technical Area:**
Must be in at least ONE of the following technical domains:
* **VLSI Design:** RTL design, logic design, digital/analog IC design, SoC design, ASIC design
* **Verification:** Functional verification, formal verification, UVM, SystemVerilog, emulation
* **Physical Design:** Floor planning, placement & routing, timing closure, STA, power analysis
* **DFT:** Design for Test, ATPG, BIST, scan chain, JTAG
* **FPGA:** FPGA design, prototyping, Xilinx, Intel/Altera
* **EDA Tools:** CAD development, EDA software engineering, algorithm development for synthesis/PnR/timing
* **Embedded Systems:** Firmware, embedded C/C++, RTOS, BSP, device drivers, microcontroller programming
* **Semiconductor Process:** Process engineering, device physics, fab operations, yield engineering
* **Architecture:** CPU/GPU/NPU/DSP architecture, microarchitecture, ISA design
* **Packaging & Test:** IC packaging, test engineering, ATE, characterization

**2. Location & Work Model:**
* **Yes Match:** Must satisfy at least ONE of:
  * Located in India (any major city)
  * Fully Remote with worldwide eligibility (no country restriction)
  * Located in a semiconductor hub worldwide (San Jose, Austin, Portland, Munich, Eindhoven, Hsinchu, Seoul, etc.) AND offers visa sponsorship or relocation
* **Maybe Match:** Jobs in locations outside India that don't explicitly mention visa sponsorship but match all other criteria
* **Location Inference:** If the job is posted by an India-based company (TCS, Wipro, HCL, Infosys, etc.) and no location is specified, assume India.

**3. Experience Level:**
* Match jobs from entry-level through senior level
* If the job requires more than 15 years of experience, mark as "no"
* Director/VP/C-level titles should be marked as "no"

**4. Application Deadline:**
* The last date of application MUST be in the future (use today's date for comparison)
* If the deadline has already passed, discard the job
* If no deadline is explicitly mentioned, assume it is still active

## Agent Instructions
When evaluating a job posting, you MUST use your web fetch tool to visit the URL to check the application deadline and read the full job description. Logically check if it fits the combinations defined above.

**Tracking Evaluations:** After evaluating a "pending" job in `jobs.json`, you MUST update that specific job's entry directly within `jobs.json` in-place. Set `"visited": "yes"`, update `"matches_requirements"` to `"yes"` (if it matched), `"maybe"` (if it is a maybe match), or `"no"` (if it was discarded), and set `"reason"` to a brief 1-sentence explanation of your decision. Do NOT delete any records from the file!
