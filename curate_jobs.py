import os
import json
import sys

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PUBLIC_DIR = r"C:\Users\vinee\vineeth_jobs"
JOBS_FILE = os.path.join(PUBLIC_DIR, "jobs.json")
json_path = JOBS_FILE
print(f"Reading from jobs file: {json_path}")

if not os.path.exists(json_path):
    print("jobs.json not found!")
    sys.exit(0)

with open(json_path, "r", encoding="utf-8") as f:
    jobs = json.load(f)

print(f"Total jobs in {json_path}: {len(jobs)}")

IRRELEVANT_KEYWORDS = [
    "verification", "uvm", "testbench", "formal verification", "dv engineer",
    "software development", "sw engineer", "firmware", "backend", "embedded",
    "frontend", "fullstack", "web developer", "it support", "sales", "hr", 
    "human resources", "finance", "marketing"
]

KEEP_KEYWORDS = [
    "power integrity", "pi", "signal integrity", "si", "packaging", "thermal",
    "cad", "methodology", "eda", "physical design", "floor planning", "placement",
    "routing", "vlsi", "soc", "asic", "principal", "director", "manager",
    "technical leader", "staff", "architect", "hardware", "analog", "digital",
    "pdn", "emir", "ir drop", "system power integrity", "si/pi"
]

curated = []
skipped_processed = 0
skipped_type = 0

for job in jobs:
    job_id = job.get("id", job.get("job_id"))
    title = (job.get("title", job.get("job_title")) or "").lower()
    
    if job.get("visited") == "yes":
        skipped_processed += 1
        continue

    is_irrelevant = False
    for kw in IRRELEVANT_KEYWORDS:
        if kw in title:
            # Let's unconditionally keep strong match roles
            if any(k in title for k in KEEP_KEYWORDS):
                continue
            is_irrelevant = True
            break
            
    if is_irrelevant:
        skipped_type += 1
        continue

    curated.append(job)

print(f"Skipped already processed: {skipped_processed}")
print(f"Skipped irrelevant job types: {skipped_type}")
print(f"Curated jobs remaining for LLM evaluation: {len(curated)}")

curated_path = os.path.join(PUBLIC_DIR, "curated_jobs.json")
with open(curated_path, "w", encoding="utf-8") as f:
    json.dump(curated, f, indent=2, ensure_ascii=False)
print(f"Saved curated list to {curated_path}")
