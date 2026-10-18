from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from gtm_pipeline.selection import InputError, domain, select, validate_profile

ROOT = Path(__file__).resolve().parents[1]


class SelectionTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / "examples/model-evaluation"
        self.profile, self.candidates, self.exclusions = (
            json.loads((folder / f"{name}.json").read_text())
            for name in ("profile", "candidates", "exclusions"))

    def run_batch(self, count=2):
        return select(self.profile, self.candidates, self.exclusions, count, "2026-10-09")

    def test_selection_reserves_exclusions_and_shortfall(self):
        result = self.run_batch(4)
        self.assertEqual((result["selected_n"], result["shortfall"]), (3, 1))
        self.assertEqual(len(result["excluded"]), 2)
        self.assertEqual(result["selected"][0]["domain"], "model-evaluation-alpha.example")
        self.assertEqual(result["reviewed_n"], 0)
        self.assertEqual(result["verified_added_n"], 0)
        self.assertEqual(self.run_batch()["reserves"][0]["domain"], "model-evaluation-beta.example")

    def test_optional_unknown_remains_visible(self):
        beta = next(row for row in self.run_batch(10)["selected"] if "beta" in row["domain"])
        self.assertEqual(beta["score"], 90)
        self.assertEqual(beta["unknowns"], ["scale-signal"])

    def test_mixed_case_www_normalization(self):
        self.assertEqual(domain("https://WWW.Example.com/product"), "example.com")
        self.assertEqual(domain("api.example.com"), "api.example.com")

    def test_suppression_follows_transitive_aliases(self):
        self.candidates["records"][0]["aliases"] = ["renamed.example"]
        self.exclusions["records"] += [
            {"domain": "renamed.example", "aliases": ["old.example"], "reason": "Merged company"},
            {"domain": "old.example", "reason": "Do not contact"}]
        result = self.run_batch(10)
        row = next(row for row in result["excluded"] if "alpha" in row["domain"])
        self.assertIn("Do not contact", row["reasons"])

    def test_duplicates_are_held_instead_of_picking_a_convenient_assessment(self):
        duplicate = deepcopy(self.candidates["records"][0])
        duplicate["domain"] = "WWW.MODEL-EVALUATION-ALPHA.EXAMPLE"
        duplicate["assessments"]["production-workload"]["verdict"] = "fail"
        self.candidates["records"].append(duplicate)
        result = self.run_batch(10)
        self.assertFalse(any("alpha" in row["domain"] for row in result["selected"]))

    def test_stale_and_future_required_evidence_is_unknown(self):
        for observed_at in ("2020-01-01", "2026-10-10"):
            with self.subTest(observed_at=observed_at):
                self.candidates["records"][0]["assessments"]["production-workload"]["observed_at"] = observed_at
                result = self.run_batch(10)
                self.assertFalse(any("alpha" in row["domain"] for row in result["selected"]))

    def test_missing_required_criterion_holds_candidate(self):
        del self.candidates["records"][0]["assessments"]["production-workload"]
        self.assertFalse(any("alpha" in row["domain"] for row in self.run_batch(10)["selected"]))

    def test_incomplete_or_stale_exclusions_are_provisional(self):
        self.exclusions["coverage"]["pending_batches"] = "unknown"
        self.exclusions["as_of"] = "2026-09-01"
        result = self.run_batch()
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(len(result["coverage_gaps"]), 2)

    def test_wrong_funnel_fails(self):
        self.exclusions["funnel"] = "other-channel"
        with self.assertRaises(InputError):
            self.run_batch()

    def test_wrong_profile_version_fails(self):
        self.candidates["profile_version"] = "older-v1"
        with self.assertRaises(InputError):
            self.run_batch()

    def test_malformed_evidence_fails_before_selection(self):
        self.candidates["records"][0]["assessments"]["production-workload"]["source_url"] = "file:///private/secret"
        with self.assertRaises(InputError):
            self.run_batch()

    def test_invalid_weights_and_counts(self):
        for count in (0, -1, True, 1.5):
            with self.subTest(count=count), self.assertRaises(InputError):
                self.run_batch(count)
        self.profile["criteria"][0]["weight"] = 5
        with self.assertRaises(InputError):
            validate_profile(self.profile)

    def test_profile_cannot_select_without_any_eligibility_gate(self):
        for criterion in self.profile["criteria"]:
            criterion["required"] = False
        with self.assertRaises(InputError):
            validate_profile(self.profile)

    def test_selection_is_deterministic_and_does_not_mutate_inputs(self):
        original = deepcopy(self.candidates)
        first = self.run_batch()
        self.assertEqual(original, self.candidates)
        self.candidates["records"].reverse()
        second = self.run_batch()
        self.assertEqual(first["selected"], second["selected"])

    def test_unrelated_business_uses_same_engine(self):
        folder = ROOT / "examples/warehouse-software"
        inputs = [json.loads((folder / f"{name}.json").read_text())
                  for name in ("profile", "candidates", "exclusions")]
        result = select(*inputs, 2, "2026-10-09")
        self.assertEqual(result["selected_n"], 2)
        self.assertEqual(result["profile_id"], "warehouse-software")

    def test_cli_writes_hashed_isolated_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            command = [sys.executable, "-m", "gtm_pipeline", "next-companies"]
            for field in ("profile", "candidates", "exclusions"):
                command += [f"--{field}", str(ROOT / f"examples/model-evaluation/{field}.json")]
            command += ["--count", "2", "--as-of", "2026-10-09", "--output", temp]
            paths = []
            for _ in range(2):
                run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                folder = Path(json.loads(run.stdout)["output"])
                paths.append(folder)
                manifest = json.loads((folder / "manifest.json").read_text())
                self.assertEqual(manifest["inputs"]["profile"]["sha256"], hashlib.sha256(
                    (ROOT / "examples/model-evaluation/profile.json").read_bytes()).hexdigest())
                self.assertEqual(manifest["output_sha256"], hashlib.sha256(
                    (folder / "next-companies.json").read_bytes()).hexdigest())
                self.assertTrue((folder / "next-companies.md").exists())
            self.assertNotEqual(*paths)

    def test_cli_invalid_inputs_do_not_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            run = subprocess.run([sys.executable, "-m", "gtm_pipeline", "next-companies",
                "--profile", str(ROOT / "examples/model-evaluation/profile.json"),
                "--candidates", str(ROOT / "examples/warehouse-software/candidates.json"),
                "--exclusions", str(ROOT / "examples/model-evaluation/exclusions.json"),
                "--count", "2", "--as-of", "2026-10-09", "--output", temp],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(list(Path(temp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
