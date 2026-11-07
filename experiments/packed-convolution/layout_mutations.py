"""Scoped semantic mutations for packed-layout refinement checks."""

SOURCE = "native/verified/packed_layout.rs"
MUTATIONS = (
    (
        "write-nonzero-padding",
        "pub fn pack_coefficients(",
        "crate::toom_words::zero(\n            &mut dst[destination_pos + layout.coefficient_limbs..destination_pos + slot_limbs],\n        );",
        "crate::toom_words::zero(&mut []);",
    ),
    (
        "extract-guard-instead-of-coefficient",
        "pub fn extract_coefficients(",
        "&src[source_pos..source_pos + layout.coefficient_limbs],",
        "&src[source_pos + (slot_limbs - layout.coefficient_limbs)..source_pos + slot_limbs],",
    ),
    (
        "wrong-precision-error",
        "pub fn checked_layout(",
        "return Err(PackedLayoutError::InvalidPrecision);",
        "return Err(PackedLayoutError::SlotTooNarrow);",
    ),
)


def mutate(source, function, before, after):
    start = source.find(function)
    if start < 0:
        raise ValueError("mutation function anchor is missing")
    end = source.find("\npub ", start + len(function))
    if end < 0:
        end = len(source)
    body = source[start:end]
    if body.count(before) != 1:
        raise ValueError("mutation anchor is not unique in its function")
    return source[:start] + body.replace(before, after) + source[end:]


def check_anchors(source):
    for name, function, before, after in MUTATIONS:
        mutated = mutate(source, function, before, after)
        if mutated == source or mutated.count(after) < 1:
            raise ValueError("mutation did not change its intended function: " + name)
    return {"status": "pass", "mutants": [item[0] for item in MUTATIONS],
            "scope": SOURCE, "verifier_executed": False}
