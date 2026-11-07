#!/usr/bin/env python3
"""Independent integer oracle and runtime-client fixture generator."""
import argparse
import json
from pathlib import Path
import random

WORD_BITS = 64
WORD_MASK = (1 << WORD_BITS) - 1
USIZE_MAX = (1 << 64) - 1


def coefficient_limbs(precision):
    if precision <= 0:
        raise ValueError("precision must be positive")
    return (precision + WORD_BITS - 1) // WORD_BITS


def integer_from_words(words):
    return sum(word << (WORD_BITS * i) for i, word in enumerate(words))


def words_from_integer(value, limbs):
    if value < 0 or value >= 1 << (WORD_BITS * limbs):
        raise ValueError("integer does not fit the requested word count")
    return [(value >> (WORD_BITS * i)) & WORD_MASK for i in range(limbs)]


def flatten(values):
    return [word for value in values for word in value]


def literal(words):
    return "[" + ", ".join(f"{word}u64" for word in words) + "]"


def classify_layout_error(direction, count, precision, slot_limbs, source_words, destination_words):
    if precision == 0:
        return "InvalidPrecision"
    coeff_limbs = coefficient_limbs(precision)
    if slot_limbs < coeff_limbs:
        return "SlotTooNarrow"
    if count > USIZE_MAX // coeff_limbs or count > USIZE_MAX // slot_limbs:
        return "LengthOverflow"
    expected_source = count * (slot_limbs if direction == "extract" else coeff_limbs)
    expected_destination = count * (coeff_limbs if direction == "extract" else slot_limbs)
    if source_words != expected_source:
        return "SourceLengthMismatch"
    if destination_words != expected_destination:
        return "DestinationLengthMismatch"
    return None


def valid_case(values, precision, slot_limbs, case_id):
    coeff_limbs = coefficient_limbs(precision)
    modulus = 1 << precision
    source_chunks = [words_from_integer(value, coeff_limbs) for value in values]
    source = flatten(source_chunks)

    expected_slots = []
    for chunk in source_chunks:
        coefficient = integer_from_words(chunk) % modulus
        expected_slots.append(words_from_integer(coefficient, slot_limbs))
    packed = flatten(expected_slots)

    recovered_chunks = []
    for slot in expected_slots:
        coefficient = integer_from_words(slot) % modulus
        recovered_chunks.append(words_from_integer(coefficient, coeff_limbs))
    recovered = flatten(recovered_chunks)

    assert recovered == source
    assert all(integer_from_words(slot) < modulus for slot in expected_slots)
    return dict(id=case_id, precision=precision, slot_limbs=slot_limbs,
                count=len(values), source=source, packed=packed, recovered=recovered)


def rust_valid_case(case):
    i = case["id"]
    return f"""    {{
        let src: [u64; {len(case['source'])}] = {literal(case['source'])};
        let mut packed: [u64; {len(case['packed'])}] = [u64::MAX; {len(case['packed'])}];
        let expected_packed: [u64; {len(case['packed'])}] = {literal(case['packed'])};
        let result = pack_coefficients(&mut packed, &src, {case['count']}, {case['precision']}, {case['slot_limbs']});
        assert!(matches!(result, Ok(())), "pack case {i}");
        assert_eq!(packed, expected_packed, "packed words case {i}");
        let mut recovered: [u64; {len(case['recovered'])}] = [u64::MAX; {len(case['recovered'])}];
        let expected_recovered: [u64; {len(case['recovered'])}] = {literal(case['recovered'])};
        let result = extract_coefficients(&mut recovered, &packed, {case['count']}, {case['precision']}, {case['slot_limbs']});
        assert!(matches!(result, Ok(())), "extract case {i}");
        assert_eq!(recovered, expected_recovered, "recovered words case {i}");
    }}
"""


def rust_error_case(case):
    error = case["error"]
    source = case["source"]
    destination = case["destination"]
    direction = case["direction"]
    call = (f"pack_coefficients(&mut dst, &src, {case['count']}, {case['precision']}, {case['slot_limbs']})"
            if direction == "pack" else
            f"extract_coefficients(&mut dst, &src, {case['count']}, {case['precision']}, {case['slot_limbs']})")
    return f"""    {{
        let src: [u64; {len(source)}] = {literal(source)};
        let mut dst: [u64; {len(destination)}] = {literal(destination)};
        let before = dst;
        let result = {call};
        assert!(matches!(result, Err(PackedLayoutError::{error})), "{direction} error {case['id']}");
        assert_eq!(dst, before, "destination changed on error {case['id']}");
    }}
"""


def check(output):
    output = Path(output)
    if output.exists():
        raise RuntimeError("use a fresh output directory")
    output.mkdir(parents=True)
    if USIZE_MAX != (1 << 64) - 1:
        raise RuntimeError("fixture contract is pinned to 64-bit usize")

    rng = random.Random(0x5041434B)
    cases = []
    case_id = 0
    for precision in (1, 2, 31, 32, 33, 63, 64, 65, 66, 127, 128, 129, 191, 192, 193, 255):
        coeff_limbs = coefficient_limbs(precision)
        for count in (0, 1, 2, 5):
            values = [rng.randrange(1 << precision) for _ in range(count)]
            for padding in (0, 1, 3):
                slot_limbs = coeff_limbs + padding
                cases.append(valid_case(values, precision, slot_limbs, case_id))
                case_id += 1
        # Maximal, zero, and mixed limbs catch top masks and carry boundaries.
        modulus = 1 << precision
        values = [modulus - 1, 0, min(modulus - 1, (1 << min(precision, 64)) - 1)]
        cases.append(valid_case(values, precision, coeff_limbs + 2, case_id))
        case_id += 1

    errors = []

    def add_error(direction, name, count, precision, slot_limbs, source, destination):
        actual = classify_layout_error(direction, count, precision, slot_limbs,
                                        len(source), len(destination))
        if actual != name:
            raise AssertionError((direction, name, actual, count, precision, slot_limbs,
                                  len(source), len(destination)))
        errors.append(dict(id=len(errors), direction=direction, error=name, count=count,
                           precision=precision, slot_limbs=slot_limbs,
                           source=source, destination=destination))

    # Metadata failures must be returned before length checks or writes.
    add_error("pack", "InvalidPrecision", 0, 0, 0, [], [91])
    add_error("extract", "InvalidPrecision", 0, 0, 0, [], [92])
    add_error("pack", "SlotTooNarrow", 0, 1, 0, [], [921])
    add_error("extract", "SlotTooNarrow", 0, 1, 0, [], [922])
    add_error("pack", "SlotTooNarrow", 1, 65, 1, [7, 0], [93])
    add_error("extract", "SlotTooNarrow", 1, 65, 1, [7], [94])
    add_error("pack", "LengthOverflow", USIZE_MAX, 128, 2, [], [95])
    add_error("extract", "LengthOverflow", USIZE_MAX, 128, 2, [], [96])
    widest_precision_limbs = coefficient_limbs(USIZE_MAX)
    add_error("pack", "LengthOverflow", USIZE_MAX, USIZE_MAX,
              widest_precision_limbs, [], [961])
    add_error("extract", "LengthOverflow", USIZE_MAX, USIZE_MAX,
              widest_precision_limbs, [], [962])
    add_error("pack", "SourceLengthMismatch", 1, USIZE_MAX,
              widest_precision_limbs, [], [963])
    add_error("extract", "SourceLengthMismatch", 1, USIZE_MAX,
              widest_precision_limbs, [], [964])
    add_error("pack", "LengthOverflow", USIZE_MAX // 2 + 1, 1, 2, [], [97])
    add_error("extract", "LengthOverflow", USIZE_MAX // 2 + 1, 1, 2, [], [98])
    add_error("pack", "SourceLengthMismatch", 1, 65, 3, [1], [99, 99, 99])
    add_error("pack", "DestinationLengthMismatch", 1, 65, 3, [1, 0], [99, 99])
    add_error("extract", "SourceLengthMismatch", 1, 65, 3, [1, 0], [99, 99])
    add_error("extract", "DestinationLengthMismatch", 1, 65, 3, [1, 0, 0], [99])

    client = [
        "extern crate verigmp;",
        "use verigmp::packed_layout::{extract_coefficients, pack_coefficients, PackedLayoutError};",
        "fn main() {",
        *(rust_valid_case(case) for case in cases),
        *(rust_error_case(case) for case in errors),
        "}",
        "",
    ]
    (output / "runtime-cases.rs").write_text("\n".join(client), encoding="utf-8")
    (output / "alias-negative.rs").write_text(
        "\n".join((
            "extern crate verigmp;",
            "use verigmp::packed_layout::pack_coefficients;",
            "fn main() {",
            "    let mut words = [1u64, 0u64];",
            "    let _ = pack_coefficients(&mut words, &words, 1, 65, 2);",
            "}",
            "",
        )), encoding="utf-8")
    with (output / "oracle-cases.jsonl").open("w", encoding="utf-8") as stream:
        for case in cases:
            stream.write(json.dumps(case, sort_keys=True) + "\n")
    with (output / "error-cases.jsonl").open("w", encoding="utf-8") as stream:
        for case in errors:
            stream.write(json.dumps(case, sort_keys=True) + "\n")
    return dict(status="pass", scope="independent fixture/oracle generation only",
                valid_cases=len(cases), error_cases=len(errors),
                precision_boundaries=[1, 63, 64, 65, 127, 128, 129, 255],
                runtime_executed=False, rust_client="runtime-cases.rs",
                borrow_checker_fixture="alias-negative.rs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.output), indent=2))
