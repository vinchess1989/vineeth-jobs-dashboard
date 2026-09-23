import os
import json
import subprocess
import urllib.request
import random
import time
from datetime import datetime

PUBLIC_DIR = r"C:\Users\vinee\vineeth_jobs"
JOBS_FILE = os.path.join(PUBLIC_DIR, "jobs.json")
CURATED_FILE = os.path.join(PUBLIC_DIR, "curated_jobs.json")
REQ_FILE = os.path.join(PUBLIC_DIR, "job_requirements.md")
SAMPLES_DIR = os.path.join(PUBLIC_DIR, "samples_for_review")

os.makedirs(SAMPLES_DIR, exist_ok=True)

# LLM Configuration
LLM_ENDPOINT = os.environ.get("LOCAL_LLM_ENDPOINT", "http://localhost:1234/v1/chat/completions")

def get_active_model():
    """Ask LM Studio (via `lms ps`) which chat model is actually loaded right now.
    NOTE: the OpenAI-compatible /v1/models HTTP endpoint is NOT usable for this - it lists
    every downloaded model eligible for LM Studio's just-in-time loading, not just what's
    currently resident in memory, so picking the first entry from it (the old approach here)
    could silently JIT-load an unrelated model - e.g. it picked Hermes back up over an
    already-loaded Gemma purely because of /v1/models' listing order. `lms ps` only ever
    lists genuinely loaded models, so it's the only trustworthy source. Mirrors
    get_active_llm_model() in scraper.py, which had the same bug fixed already."""
    try:
        lms_exe = os.path.join(os.environ.get("USERPROFILE", ""), ".lmstudio", "bin", "lms.exe")
        result = subprocess.run([lms_exe, "ps", "--json"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            models = json.loads(result.stdout)
            chat_models = [m["identifier"] for m in models if m.get("type") == "llm"]
            if chat_models:
                return chat_models[0]
    except Exception as e:
        print(f"Warning: Could not query lms ps for active model: {e}")
    return os.environ.get("LOCAL_LLM_MODEL", "hermes-3-llama-3.1-8b")

MODEL_NAME = get_active_model()
print(f"Dynamically selected active local model: {MODEL_NAME}")

def load_requirements():
    with open(REQ_FILE, "r", encoding="utf-8") as f:
        return f.read()

def call_local_llm(prompt):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a strict, highly analytical technical recruiter evaluating job descriptions for a Senior Staff/Technical Leader hardware engineering profile. You only output valid JSON without any markdown formatting or preamble."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    req = urllib.request.Request(
        LLM_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"LLM Call Failed: {e}")
        return None

def main():
    if not os.path.exists(CURATED_FILE):
        print("No curated_jobs.json found.")
        return

    with open(CURATED_FILE, "r", encoding="utf-8") as f:
        curated_jobs = json.load(f)

    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        all_jobs = json.load(f)

    job_map = {j.get("id", j.get("job_id")): j for j in all_jobs}
    requirements = load_requirements()

    evaluated_count = 0

    for c_job in curated_jobs:
        job_id = c_job.get("id", c_job.get("job_id"))
        master_job = job_map.get(job_id)
        
        if not master_job:
            continue
            
        if master_job.get("visited") == "yes" and master_job.get("matches_requirements"):
            continue

        desc_link = master_job.get("description_file")
        if not desc_link:
            desc_text = master_job.get("description")
            if not desc_text:
                continue
        else:
            desc_path = os.path.join(PUBLIC_DIR, desc_link)
            if not os.path.exists(desc_path):
                continue
            with open(desc_path, "r", encoding="utf-8") as f:
                desc_text = f.read()

        print(f"Evaluating Job {job_id} - {master_job.get('title')}...")

        prompt = f"""Evaluate the following job description against the provided Job Requirements.

JOB REQUIREMENTS:
{requirements}

JOB POSTING:
Title: {master_job.get('title')}
Company: {master_job.get('company')}
Location: {master_job.get('location')}

DESCRIPTION:
{desc_text[:30000]}

INSTRUCTIONS:
Decide if this job matches the requirements.
Output ONLY a JSON object exactly like this:
{{
    "matches_requirements": "yes", // or "no" or "maybe"
    "reason": "One short sentence explaining why."
}}
"""
        
        response_text = call_local_llm(prompt)
        if not response_text:
            continue
            
        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
                
            decision_data = json.loads(clean_text)
            
            master_job["visited"] = "yes"
            master_job["matches_requirements"] = decision_data.get("matches_requirements", "no").lower()
            master_job["reason"] = decision_data.get("reason", "No reason provided")
            master_job["ai_evaluated"] = "yes"
            master_job["eval_model"] = MODEL_NAME
            master_job["evaluation_date"] = datetime.now().isoformat()
            
            print(f"  -> Decision: {master_job['matches_requirements']} ({master_job['reason']})")
            evaluated_count += 1
            
            # Sampling logic
            if random.random() < 0.2:
                sample_path = os.path.join(SAMPLES_DIR, f"{job_id}_sample.txt")
                with open(sample_path, "w", encoding="utf-8") as f:
                    f.write(f"JOB ID: {job_id}\n")
                    f.write(f"TITLE: {master_job.get('title')}\n")
                    f.write(f"DECISION: {master_job['matches_requirements']}\n")
                    f.write(f"REASON: {master_job['reason']}\n\n")
                    f.write(f"=== LLM RAW OUTPUT ===\n{response_text}\n")
                print("  [SAMPLING] Saved evaluation sample for review.")
            
            if evaluated_count % 5 == 0:
                with open(JOBS_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_jobs, f, indent=2, ensure_ascii=False)
                    
            time.sleep(1)
            
        except json.JSONDecodeError as e:
            print(f"  -> Error parsing JSON from LLM: {e}")
            print(f"     Raw response: {response_text}")

    if evaluated_count > 0:
        with open(JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully evaluated {evaluated_count} new jobs and updated jobs.json")
    else:
        print("\nNo new jobs to evaluate.")

if __name__ == "__main__":
    main()
