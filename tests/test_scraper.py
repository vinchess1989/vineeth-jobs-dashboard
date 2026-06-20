"""Unit tests for vineeth_jobs scraper.py logic.

Run with:  pytest tests/ -v
"""
import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import scraper


# ---------------------------------------------------------------------------
# extract_json_from_text
# ---------------------------------------------------------------------------

class TestExtractJsonFromText:
    def test_plain_json(self):
        result = scraper.extract_json_from_text('{"match": "yes", "reason": "ok"}')
        assert result["match"] == "yes"

    def test_json_with_markdown_fence(self):
        text = '```json\n{"match": "no", "reason": "expired"}\n```'
        result = scraper.extract_json_from_text(text)
        assert result["match"] == "no"

    def test_json_embedded_in_prose(self):
        text = 'Here is the result: {"match": "maybe", "reason": "border case"} — done.'
        result = scraper.extract_json_from_text(text)
        assert result["match"] == "maybe"

    def test_raises_on_invalid(self):
        with pytest.raises(Exception):
            scraper.extract_json_from_text("no json here at all")


# ---------------------------------------------------------------------------
# save_history_snapshot
# ---------------------------------------------------------------------------

class TestSaveHistorySnapshot:
    def test_creates_history_file(self, tmp_path):
        hist_path = str(tmp_path / "jobs_history.json")
        jobs = [
            {"matches_requirements": "yes"},
            {"matches_requirements": "no"},
            {"matches_requirements": "maybe"},
        ]
        with patch.object(scraper, "HISTORY_FILE", hist_path):
            scraper.save_history_snapshot(jobs)

        assert os.path.exists(hist_path)
        with open(hist_path) as f:
            history = json.load(f)
        assert len(history) == 1
        snap = history[0]
        assert snap["total"] == 3
        assert snap["yes"] == 1
        assert snap["no"] == 1
        assert snap["maybe"] == 1
        assert snap["pending"] == 0

    def test_appends_to_existing_history(self, tmp_path):
        hist_path = str(tmp_path / "jobs_history.json")
        existing = [{"timestamp": "2026-06-18T12:00:00", "total": 10, "yes": 3, "no": 5, "maybe": 2, "pending": 0}]
        with open(hist_path, "w") as f:
            json.dump(existing, f)

        jobs = [{"matches_requirements": "yes"}, {"matches_requirements": "pending"}]
        with patch.object(scraper, "HISTORY_FILE", hist_path):
            scraper.save_history_snapshot(jobs)

        with open(hist_path) as f:
            history = json.load(f)
        assert len(history) == 2
        assert history[1]["total"] == 2
        assert history[1]["yes"] == 1
        assert history[1]["pending"] == 1

    def test_handles_corrupt_history_gracefully(self, tmp_path):
        hist_path = str(tmp_path / "jobs_history.json")
        with open(hist_path, "w") as f:
            f.write("not valid json {{{{")

        jobs = [{"matches_requirements": "yes"}]
        with patch.object(scraper, "HISTORY_FILE", hist_path):
            scraper.save_history_snapshot(jobs)  # must not raise

        with open(hist_path) as f:
            history = json.load(f)
        assert len(history) == 1


# ---------------------------------------------------------------------------
# generate_history_from_backups
# ---------------------------------------------------------------------------

class TestGenerateHistoryFromBackups:
    def test_generates_from_two_backup_files(self, tmp_path, backup_dir):
        hist_path = str(tmp_path / "jobs_history.json")
        with patch.object(scraper, "HISTORY_FILE", hist_path), \
             patch.object(scraper, "BASE_DIR", str(tmp_path)):
            scraper.generate_history_from_backups()

        assert os.path.exists(hist_path)
        with open(hist_path) as f:
            history = json.load(f)
        assert len(history) == 2
        assert history[0]["timestamp"] == "2026-06-18T12:00:00"
        assert history[0]["total"] == 2
        assert history[0]["yes"] == 1
        assert history[1]["total"] == 3
        assert history[1]["maybe"] == 1

    def test_skips_if_history_already_exists(self, tmp_path, backup_dir):
        hist_path = str(tmp_path / "jobs_history.json")
        # Pre-create so generate_history_from_backups should bail early
        with open(hist_path, "w") as f:
            json.dump([{"existing": True}], f)

        with patch.object(scraper, "HISTORY_FILE", hist_path), \
             patch.object(scraper, "BASE_DIR", str(tmp_path)):
            scraper.generate_history_from_backups()

        with open(hist_path) as f:
            history = json.load(f)
        assert history == [{"existing": True}]  # unchanged

    def test_no_backups_creates_no_file(self, tmp_path):
        hist_path = str(tmp_path / "jobs_history.json")
        empty_backup_dir = tmp_path / "backups"
        empty_backup_dir.mkdir()
        with patch.object(scraper, "HISTORY_FILE", hist_path), \
             patch.object(scraper, "BASE_DIR", str(tmp_path)):
            scraper.generate_history_from_backups()
        assert not os.path.exists(hist_path)


# ---------------------------------------------------------------------------
# check_requirements_update — flags non-done jobs when hash changes
# ---------------------------------------------------------------------------

class TestCheckRequirementsUpdate:
    def _write_checkpoint(self, tmp_path, req_hash):
        cp = {"requirements_hash": req_hash}
        (tmp_path / "checkpoint.json").write_text(json.dumps(cp), encoding="utf-8")

    def test_non_done_jobs_flagged_when_hash_changes(self, jobs_file, req_file, tmp_path):
        self._write_checkpoint(tmp_path, "oldhash000")

        with patch.object(scraper, "JOBS_FILE", jobs_file), \
             patch.object(scraper, "REQ_FILE", req_file), \
             patch.object(scraper, "CHECKPOINT_FILE", str(tmp_path / "checkpoint.json")):
            scraper.check_requirements_update()

        with open(jobs_file) as f:
            jobs = json.load(f)

        yes_job  = next(j for j in jobs if j["matches_requirements"] == "yes")
        no_job   = next(j for j in jobs if j["matches_requirements"] == "no")
        done_job = next(j for j in jobs if j["user_review"] == "done")

        assert yes_job.get("needs_re_review") is True
        assert no_job.get("needs_re_review") is True   # vineeth flags all non-done
        assert done_job.get("needs_re_review") is None  # done jobs never touched

    def test_no_flag_when_hash_unchanged(self, jobs_file, req_file, tmp_path):
        import hashlib
        with open(req_file, "rb") as f:
            current_hash = hashlib.md5(f.read()).hexdigest()
        self._write_checkpoint(tmp_path, current_hash)

        with patch.object(scraper, "JOBS_FILE", jobs_file), \
             patch.object(scraper, "REQ_FILE", req_file), \
             patch.object(scraper, "CHECKPOINT_FILE", str(tmp_path / "checkpoint.json")):
            scraper.check_requirements_update()

        with open(jobs_file) as f:
            jobs = json.load(f)
        assert all(j.get("needs_re_review") is None for j in jobs)


# ---------------------------------------------------------------------------
# clean_blocked_jobs — title keyword filtering
# ---------------------------------------------------------------------------

class TestCleanBlockedJobs:
    def test_director_title_moved_to_deleted(self, tmp_path):
        jobs = [
            {"url": "https://example.com/1", "title": "Director of VLSI Design",
             "matches_requirements": "yes", "user_review": "pending", "deadline": "N/A"},
            {"url": "https://example.com/2", "title": "ASIC Engineer",
             "matches_requirements": "yes", "user_review": "pending", "deadline": "N/A"},
        ]
        jobs_path = str(tmp_path / "jobs.json")
        deleted_path = str(tmp_path / "deleted.json")
        with open(jobs_path, "w") as f:
            json.dump(jobs, f)

        with patch.object(scraper, "JOBS_FILE", jobs_path), \
             patch.object(scraper, "DELETED_FILE", deleted_path):
            scraper.clean_blocked_jobs()

        with open(jobs_path) as f:
            remaining = json.load(f)
        with open(deleted_path) as f:
            deleted = json.load(f)

        assert len(remaining) == 1
        assert remaining[0]["title"] == "ASIC Engineer"
        assert len(deleted) == 1
        assert "director" in deleted[0]["deletion_reason"].lower()

    def test_done_jobs_not_deleted_for_expired_deadline(self, tmp_path):
        jobs = [
            {"url": "https://example.com/1", "title": "RTL Engineer",
             "matches_requirements": "yes", "user_review": "done", "deadline": "2020-01-01"},
        ]
        jobs_path = str(tmp_path / "jobs.json")
        with open(jobs_path, "w") as f:
            json.dump(jobs, f)

        with patch.object(scraper, "JOBS_FILE", jobs_path), \
             patch.object(scraper, "DELETED_FILE", str(tmp_path / "deleted.json")):
            scraper.clean_blocked_jobs()

        with open(jobs_path) as f:
            remaining = json.load(f)
        assert len(remaining) == 1  # done jobs are immune to deadline expiry


# ---------------------------------------------------------------------------
# poll_firebase_feedback — user_reason cleared on blank override
# ---------------------------------------------------------------------------

class TestPollFirebaseFeedback:
    JOB_URL = "https://example.com/job/1"

    def _make_firestore_response(self, feedback_type, extra_fields=None):
        fields = {
            "status":   {"stringValue": "unread"},
            "type":     {"stringValue": feedback_type},
            "url":      {"stringValue": self.JOB_URL},
        }
        if extra_fields:
            fields.update(extra_fields)
        return {"documents": [{"name": "projects/p/databases/(default)/documents/user_feedback/doc1",
                               "fields": fields}]}

    @patch("scraper.requests.patch")
    @patch("scraper.requests.get")
    def test_negative_feedback_flips_match_to_no(self, mock_get, mock_patch, jobs_file):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: self._make_firestore_response(
                "negative", {"reason": {"stringValue": ""}}
            )
        )
        mock_patch.return_value = MagicMock(status_code=200)

        with patch.object(scraper, "JOBS_FILE", jobs_file), \
             patch.object(scraper, "REQ_FILE", "nonexistent_req.md"):
            scraper.poll_firebase_feedback()

        with open(jobs_file) as f:
            jobs = json.load(f)
        job = next(j for j in jobs if j["url"] == self.JOB_URL)
        assert job["matches_requirements"] == "no"

    @patch("scraper.requests.patch")
    @patch("scraper.requests.get")
    def test_user_review_update_applied(self, mock_get, mock_patch, jobs_file):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: self._make_firestore_response(
                "user_review_update",
                {"user_review": {"stringValue": "done"}}
            )
        )
        mock_patch.return_value = MagicMock(status_code=200)

        with patch.object(scraper, "JOBS_FILE", jobs_file), \
             patch.object(scraper, "REQ_FILE", "nonexistent_req.md"):
            scraper.poll_firebase_feedback()

        with open(jobs_file) as f:
            jobs = json.load(f)
        job = next(j for j in jobs if j["url"] == self.JOB_URL)
        assert job["user_review"] == "done"

    @patch("scraper.requests.get", return_value=MagicMock(status_code=403))
    def test_graceful_on_403(self, mock_get, jobs_file):
        with patch.object(scraper, "JOBS_FILE", jobs_file):
            scraper.poll_firebase_feedback()  # must not raise
