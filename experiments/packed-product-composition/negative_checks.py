"""Scoped semantic mutations and invalid-domain/borrow fixtures."""
import re

from verus_logs import ALLOWED_VC, ALL_SUMMARIES, ERROR_LINE, FATAL_DIAGNOSTIC

MODEL = "native/specs/packed_product.rs"
CONSUMER = "experiments/packed-product-composition/consumer.rs"
MUTATIONS = (
    ("insufficient-guard", MODEL,
     "count <= pow(2, (q - 2 * p) as nat)",
     "count <= pow(2, (q - 2 * p + 1) as nat)"),
    ("nonzero-final-tail", MODEL,
     "coefficients(output, 2 * count, q)[(2 * count - 1) as int] == 0",
     "coefficients(output, 2 * count, q)[(2 * count - 1) as int] == 1"),
    ("square-instead-of-product", CONSUMER,
     "toom_multiply::full(product, packed_left, packed_right, scratch, 24);",
     "toom_multiply::full(product, packed_left, packed_left, scratch, 24);"),
    ("extract-input-precision", CONSUMER,
     "layout::extract_coefficients(output, product, result_count, q, slot)",
     "layout::extract_coefficients(output, product, result_count, p, slot)"),
)


def full_semantic_rejection(text, returncode):
    summaries = re.findall(r"(?m)^verification results:: (\d+) verified, (\d+) errors$", text)
    diagnostics = [line for line in ERROR_LINE.findall(text)
                   if not line.startswith("aborting due to ")]
    return (returncode == 1 and len(summaries) == 1
            and len(ALL_SUMMARIES.findall(text)) == 1 and int(summaries[0][1]) > 0
            and bool(diagnostics) and all(line.startswith(ALLOWED_VC) for line in diagnostics)
            and FATAL_DIAGNOSTIC.search(text) is None)


def classifier_check():
    text = "error: precondition not satisfied\nverification results:: 1 verified, 1 errors\n"
    assert full_semantic_rejection(text, 1)
    assert not full_semantic_rejection(text, 0)
    assert not full_semantic_rejection(text, 2)
    assert not full_semantic_rejection(text.replace("1 errors", "0 errors"), 1)
    assert not full_semantic_rejection(text + "verification results:: 1 verified, 0 errors\n", 1)
    for fault in ("unexpected token", "solver unknown", "resource limit", "timed out",
                  "panicked", "failed to load metadata", "could not compile",
                  "error[E0308]: mismatched types"):
        assert not full_semantic_rejection(text + "error: " + fault + "\n", 1)
    return dict(status="pass", fixtures=13,
                accepts_only_complete_logical_vc_failures=True)


def invalid_call(kind):
    n, q, scratch, out = {"scratch": (1, 2, 11, 2),
                          "guard": (3, 3, 36, 6),
                          "output": (1, 2, 12, 1)}[kind]
    valid_guard = ("" if kind == "guard" else
                   f"        verigmp::packed_product::guard_domain({n}, 1, {q}, 1),\n")
    return f'''use vstd::prelude::*;
use verigmp::packed_layout as layout;
use packed_product_consumer::consume;
verus! {{
pub fn invalid_call(output: &mut [u64], left: &[u64], right: &[u64],
    packed_left: &mut [u64], packed_right: &mut [u64],
    product: &mut [u64], scratch: &mut [u64])
    requires
{valid_guard}        layout::compact_coefficients(left@, {n}, 1),
        layout::compact_coefficients(right@, {n}, 1),
        old(output)@.len() == {out}, old(packed_left)@.len() == {n},
        old(packed_right)@.len() == {n}, old(product)@.len() == {2*n},
        old(scratch)@.len() == {scratch},
{{
    let result = consume(output, left, right, packed_left, packed_right,
                         product, scratch, {n}, 1, {q}, 1);
}}
}}
'''


def alias_call(kind):
    call = ("consume(&mut output, &words, &right, &mut words, &mut packed_right, "
            "&mut product, &mut scratch, 1, 1, 2, 1)" if kind == "input" else
            "consume(&mut product, &words, &right, &mut packed_left, &mut packed_right, "
            "&mut product, &mut scratch, 1, 1, 2, 1)")
    return f'''use packed_product_consumer::consume;
fn main() {{
    let mut words = [1u64];
    let right = [1u64];
    let mut output = [0u64; 2];
    let mut packed_left = [0u64; 1];
    let mut packed_right = [0u64; 1];
    let mut product = [0u64; 2];
    let mut scratch = [0u64; 12];
    let result = {call};
}}
'''
