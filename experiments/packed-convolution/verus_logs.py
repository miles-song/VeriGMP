"""Strict Verus result classification shared by the focused layout gate."""
import re

FATAL_DIAGNOSTIC = re.compile(
    r"(?i)\bunknown\b|\brlimit\b|resource\s+limit|timed?\s*out|\btimeout\b|"
    r"time\s*limit|failed\s+to\s+typecheck|type[- ]?checking?\s+(?:failed|error)|"
    r"mismatched\s+types|internal\s+(?:compiler\s+)?error|panic(?:ked|s|ed)?|"
    r"error\[E\d+\]|(?:could\s+not|failed\s+to)\s+(?:load|compile)|"
    r"out\s+of\s+memory|segmentation\s+fault|LLVM\s+ERROR"
)
SUMMARY = re.compile(
    r"(?m)^verification results:: (\d+) verified, (\d+) errors "
    r"\(partial verification with `--verify-\*`\)$"
)
ALL_SUMMARIES = re.compile(r"(?m)^verification results:: \d+ verified, \d+ errors(?: .*)?$")
ERROR_LINE = re.compile(r"(?m)^error(?:\[[^\]]*\])?: (.*)$")
ALLOWED_VC = (
    "assertion failed",
    "postcondition not satisfied",
    "precondition not satisfied",
    "requires not satisfied",
    "invariant not satisfied",
    "loop invariant not satisfied",
    "possible arithmetic underflow/overflow",
    "possible arithmetic overflow",
    "possible arithmetic underflow",
)


def strict_semantic_rejection(text, returncode, module):
    summaries = SUMMARY.findall(text)
    all_summaries = ALL_SUMMARIES.findall(text)
    notes = re.findall(r"(?m)^note: verifying module ([A-Za-z_][A-Za-z_0-9]*)$", text)
    diagnostics = ERROR_LINE.findall(text)
    failures = [line for line in diagnostics if not line.startswith("aborting due to ")]
    return (
        returncode == 1
        and len(summaries) == 1
        and len(all_summaries) == 1
        and int(summaries[0][1]) > 0
        and notes == [module]
        and bool(failures)
        and all(line.startswith(ALLOWED_VC) for line in failures)
        and FATAL_DIAGNOSTIC.search(text) is None
    )


def self_check():
    prefix = (
        "verification results:: 10 verified, 1 errors "
        "(partial verification with `--verify-*`)\n"
        "note: verifying module packed_layout\n"
    )
    accepted = prefix + "error: postcondition not satisfied\nerror: aborting due to 1 previous error\n"
    assert strict_semantic_rejection(accepted, 1, "packed_layout")
    assert not strict_semantic_rejection(accepted, 0, "packed_layout")
    assert not strict_semantic_rejection(accepted, 2, "packed_layout")
    assert not strict_semantic_rejection(accepted, 1, "wrong_module")
    assert not strict_semantic_rejection(accepted + "verification results:: 0 verified, 0 errors\n", 1,
                                         "packed_layout")
    for diagnostic in (
        "unexpected token",
        "solver returned unknown",
        "resource limit exceeded",
        "verification timed out",
        "failed to load metadata",
        "could not compile crate",
        "panicked at verifier",
        "error[E0308]: mismatched types",
    ):
        assert not strict_semantic_rejection(prefix + "error: " + diagnostic + "\n", 1,
                                             "packed_layout")
    assert not strict_semantic_rejection(
        "verification results:: 10 verified, 0 errors\n", 0, "packed_layout")
    return {"status": "pass", "fixtures": 12,
            "requires_unique_partial_summary_and_module_note": True,
            "requires_returncode_one_and_positive_vc_errors": True,
            "rejects_parse_solver_resource_timeout_load_panic_and_type_errors": True}


if __name__ == "__main__":
    print(self_check())
