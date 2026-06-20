"""Shared fixtures for the vineeth_jobs test suite."""
import json
import os
import pytest


SAMPLE_JOBS = [
    {
        "url": "https://example.com/job/1",
        "title": "ASIC Design Engineer",
        "company": "Chipworks Inc",
        "location": "San Jose, CA",
        "matches_requirements": "yes",
        "reason": "Entry-level ASIC design role matching candidate's RTL skills.",
        "user_reason": "testing reason",
        "user_review": "pending",
        "visited": "yes",
        "source": "linkedin",
        "id": "aabbccdd",
        "posted_date": "2026-06-01",
        "deadline": "Open until filled",
    },
    {
        "url": "https://example.com/job/2",
        "title": "Director of Engineering",
        "company": "Big Semi Corp",
        "location": "Austin, TX",
        "matches_requirements": "no",
        "reason": "Senior director role — far above candidate level.",
        "user_reason": "",
        "user_review": "pending",
        "visited": "yes",
        "source": "naukri",
        "id": "11223344",
        "posted_date": "2026-05-20",
        "deadline": "2026-07-01",
    },
    {
        "url": "https://example.com/job/3",
        "title": "Verification Engineer",
        "company": "Nordic Semi",
        "location": "Bangalore, India",
        "matches_requirements": "maybe",
        "reason": "Adjacent UVM role, candidate has partial experience.",
        "user_reason": "",
        "user_review": "done",
        "visited": "yes",
        "source": "reddit",
        "id": "aabb1122",
        "posted_date": "2026-06-10",
        "deadline": "N/A",
    },
]


@pytest.fixture
def jobs_file(tmp_path):
    """Write SAMPLE_JOBS to a temp jobs.json and return its path."""
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps(SAMPLE_JOBS, indent=2), encoding="utf-8")
    return str(path)


@pytest.fixture
def req_file(tmp_path):
    """Write a minimal requirements file and return its path."""
    content = "## Hard Rejections\n* Director-level roles.\n"
    path = tmp_path / "job_requirements.md"
    path.write_text(content, encoding="utf-8")
    return str(path)


@pytest.fixture
def history_file(tmp_path):
    """Return a path to a (not-yet-created) history file in a temp dir."""
    return str(tmp_path / "jobs_history.json")


@pytest.fixture
def backup_dir(tmp_path):
    """Create a backups/ subdir with two fake backup files, return path."""
    bd = tmp_path / "backups"
    bd.mkdir()
    jobs_a = [{"matches_requirements": "yes"}, {"matches_requirements": "no"}]
    jobs_b = [{"matches_requirements": "yes"}, {"matches_requirements": "maybe"}, {"matches_requirements": "no"}]
    (bd / "jobs_backup_20260618_120000.json").write_text(json.dumps(jobs_a), encoding="utf-8")
    (bd / "jobs_backup_20260619_080000.json").write_text(json.dumps(jobs_b), encoding="utf-8")
    return str(bd)
