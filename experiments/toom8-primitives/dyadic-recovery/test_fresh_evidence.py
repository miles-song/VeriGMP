"""Regression controls for evidence acceptance; no proof or timing workload."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fresh_evidence import audit_fresh, audit_report, digest
from check_dyadic_recovery import m7_m8_gate, run_archive_audit


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BUNDLE = HERE / "evidence/fresh-20261103"
SCOPE = REPO / "experiments/toom8-primitives/interpolation"


class FreshEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with zipfile.ZipFile(BUNDLE / "evidence.zip") as archive:
            cls.saved = {name.removeprefix("interpolation/"): archive.read(name)
                         for name in archive.namelist() if name.startswith("interpolation/")}

    def reject(self, changes: dict[str, bytes], message: str) -> None:
        saved = self.saved | changes
        with self.assertRaisesRegex(ValueError, message):
            audit_report("interpolation", SCOPE, saved.__getitem__)

    def report_change(self, edit) -> dict[str, bytes]:
        report = json.loads(self.saved["verification.json"])
        edit(report)
        return {"verification.json": json.dumps(report).encode()}

    def test_frozen_bundle_passes_without_proof_or_runner_execution(self) -> None:
        result = audit_fresh(REPO, BUNDLE)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["gates"]["dyadic"]["oracle_cases"], 2688)
        self.assertEqual(result["gates"]["interpolation"]["oracle_cases"], 336)
        self.assertFalse(result["verification_rerun"])
        self.assertFalse(result["runner_reexecuted"])
        self.assertFalse(result["independent_acceptance"])

    def test_incomplete_report_is_rejected(self) -> None:
        self.reject(self.report_change(lambda r: r.update(status="running")), "incomplete")

    def test_omitted_source_is_rejected(self) -> None:
        self.reject(self.report_change(lambda r: r["source_sha256"].pop("candidate/native/lib.rs")), "source set")

    def test_captured_source_drift_is_rejected(self) -> None:
        key = "inputs/candidate/native/verified/toom8_interpolation.rs"
        self.reject({key: self.saved[key] + b"\n"}, "source mismatch")

    def test_current_candidate_source_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            scope = Path(temp)
            for rel, data in self.saved.items():
                if rel.startswith("inputs/"):
                    path = scope / rel.removeprefix("inputs/")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
            source = scope / "candidate/native/verified/toom8_interpolation.rs"
            source.write_bytes(source.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "source mismatch"):
                audit_report("interpolation", scope, self.saved.__getitem__)

    def test_unverified_compile_flag_is_rejected(self) -> None:
        def edit(report):
            next(c for c in report["commands"] if c["log"] == "library.log")["argv"].append("--no-verify")
        self.reject(self.report_change(edit), "compile command differs")

    def test_rehashed_oracle_output_still_requires_independent_answer(self) -> None:
        output = b"incorrect\n"
        def edit(report):
            report["oracle"]["output_sha256"] = digest(output)
            next(c for c in report["commands"] if c["log"] == "oracle.log")["log_sha256"] = digest(output)
        self.reject(self.report_change(edit) | {"oracle.log": output}, "oracle mismatch")

    def test_rehashed_timeout_is_not_a_semantic_mutation_rejection(self) -> None:
        log = "skip-seventh-node.log"
        diagnostic = self.saved[log] + b"\nverification timed out\n"
        def edit(report):
            next(c for c in report["commands"] if c["log"] == log)["log_sha256"] = digest(diagnostic)
            report["mutations"][0]["log_sha256"] = digest(diagnostic)
        self.reject(self.report_change(edit) | {log: diagnostic}, "nonsemantic mutation rejection")

    def test_rehashed_tool_version_drift_is_rejected(self) -> None:
        changed = self.saved["rustc.log"].replace(b"release: 1.99.1", b"release: 1.98.0")
        def edit(report):
            report["rustc"] = changed.decode()
            next(c for c in report["commands"] if c["log"] == "rustc.log")["log_sha256"] = digest(changed)
        self.reject(self.report_change(edit) | {"rustc.log": changed}, "tool version mismatch")

    def test_compiled_metadata_pair_is_required(self) -> None:
        self.reject({"candidate.vir": b"substituted metadata"}, "artifact mismatch: candidate.vir")

    def test_forged_promotion_receipt_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            receipt = json.loads((BUNDLE / "manifest.json").read_bytes())
            receipt["backend_promotion"] = True
            (bundle / "manifest.json").write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "acceptance scope"):
                audit_fresh(REPO, bundle)

    def test_zero_exit_with_failed_archive_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "failed_audit.py"
            script.write_text('print(\'{"status": "fail"}\')\n')
            result = run_archive_audit(script)
            self.assertEqual(result["returncode"], 0)
            self.assertEqual(result["status"], "fail")

    def test_live_consumer_allows_unrelated_status_progress_and_rejects_authority_drift(self) -> None:
        receipt = json.loads((BUNDLE / "consumer-VeriCount.json").read_bytes())
        status = {"modules": [dict(id=key, **value) for key, value in receipt["modules"].items()],
                  "arithmetic_dependency": receipt["arithmetic_dependency"],
                  "trusted_backend": receipt["trusted_backend_authority"]}
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            consumer = folder / "consumer"
            for rel in receipt["file_sha256"]:
                path = consumer / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(json.dumps(status).encode() if rel == "native/proof-status.json" else b"fixture\n")
                receipt["file_sha256"][rel] = digest(path.read_bytes())
            (consumer / "refinement").mkdir()
            captured = json.dumps(receipt).encode()
            (folder / "consumer.json").write_bytes(captured)
            (folder / "scope.json").write_text(json.dumps({"consumer_receipt": "consumer.json", "consumer_receipt_sha256": digest(captured)}))
            status["unrelated_module_progress"] = True
            (consumer / "native/proof-status.json").write_text(json.dumps(status))

            def git(argv, **kwargs):
                if argv[1] == "ls-tree":
                    return "160000 commit " + receipt["verigmp_gitlink"] + "\tthird_party/VeriGMP"
                return "f" * 40 if kwargs["cwd"] == consumer else receipt["verigmp_gitlink"]

            with patch("check_dyadic_recovery.HERE", folder), patch("check_dyadic_recovery.subprocess.check_output", git):
                result = m7_m8_gate(consumer)
                self.assertEqual(result["status"], "pass")
                self.assertNotEqual(result["head"], result["receipt_head"])
                self.assertNotEqual(result["proof_status_sha256"], result["receipt_proof_status_sha256"])
                status["modules"][0]["status"] = "integrated_proved"
                (consumer / "native/proof-status.json").write_text(json.dumps(status))
                with self.assertRaisesRegex(ValueError, "authority differs"):
                    m7_m8_gate(consumer)

    def test_cli_fails_on_corrupted_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            shutil.copyfile(BUNDLE / "manifest.json", bundle / "manifest.json")
            damaged = bytearray((BUNDLE / "evidence.zip").read_bytes())
            damaged[32] ^= 1
            (bundle / "evidence.zip").write_bytes(damaged)
            run = subprocess.run([sys.executable, str(HERE / "check_dyadic_recovery.py"),
                                  "--fresh-evidence", str(bundle)], cwd=bundle,
                                 capture_output=True, text=True, check=False)
            report = json.loads(run.stdout)
            self.assertEqual(run.returncode, 1, run.stderr)
            self.assertEqual(report["status"], "fail")
            self.assertIn("fresh_execution_evidence", report["audit_failures"])
            self.assertFalse(report["promotion"])


if __name__ == "__main__":
    unittest.main()
