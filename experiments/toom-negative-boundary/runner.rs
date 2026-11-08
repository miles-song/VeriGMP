//! Actual Rust-facing oracle runner for the -1-point boundary candidate.
//!
//! This file is experiment infrastructure. It imports the exact source tree
//! under test and deliberately keeps expected values outside Rust so the
//! arbitrary-integer oracle remains independent of the implementation.
#[path="../../native/lib.rs"] mod verigmp;

use std::fs;
use std::io::{self, Write};
use std::panic::{catch_unwind, AssertUnwindSafe};

const CANARY: u64 = 0x8a19_30de_5f24_67bc;
const POISON: u64 = 0xd1ce_5eed_a55a_5eed;

struct Reader {
    bytes: Vec<u8>,
    at: usize,
}

impl Reader {
    fn new(bytes: Vec<u8>) -> Self { Self { bytes, at: 0 } }

    fn take(&mut self, n: usize) -> &[u8] {
        assert!(self.at.checked_add(n).is_some());
        let end = self.at + n;
        assert!(end <= self.bytes.len());
        let out = &self.bytes[self.at..end];
        self.at = end;
        out
    }

    fn word(&mut self) -> u64 {
        u64::from_le_bytes(self.take(8).try_into().unwrap())
    }

    fn vector(&mut self) -> Vec<u64> {
        let n = usize::try_from(self.word()).unwrap();
        (0..n).map(|_| self.word()).collect()
    }
}

fn guarded(len: usize) -> Vec<u64> {
    let mut words = vec![POISON; len + 2];
    words[0] = CANARY;
    words[len + 1] = CANARY;
    words
}

fn middle(words: &mut [u64]) -> &mut [u64] {
    let end = words.len() - 1;
    &mut words[1..end]
}

fn invoke(
    op: u64,
    out: &mut [u64],
    a: &[u64],
    b: &[u64],
    scratch: &mut [u64],
    threshold: usize,
    top: u32,
) {
    match op {
        0 => verigmp::toom_multiply::full(out, a, b, scratch, threshold),
        1 => verigmp::arithmetic::mul_mod(out, a, b, scratch, top),
        2 => verigmp::arithmetic::mul_mod(out, a, a, scratch, top),
        3 => verigmp::arithmetic::square_mod(out, a, scratch, top),
        _ => panic!("unknown fixture operation {op}"),
    }
}

fn valid_fixture(path: &str) {
    let mut reader = Reader::new(fs::read(path).expect("fixture"));
    assert_eq!(reader.take(8), b"VGMPBN01");
    let count = usize::try_from(reader.word()).unwrap();
    let mut output = io::BufWriter::new(io::stdout().lock());
    for expected_id in 0..count {
        assert_eq!(usize::try_from(reader.word()).unwrap(), expected_id);
        let op = reader.word();
        let n = usize::try_from(reader.word()).unwrap();
        let threshold = usize::try_from(reader.word()).unwrap();
        let top = u32::try_from(reader.word()).unwrap();
        let _low = reader.word();
        let _split = reader.word();
        let extra = usize::try_from(reader.word()).unwrap();
        let shared = reader.word() != 0;
        let a = reader.vector();
        let b = reader.vector();
        assert_eq!(a.len(), n);
        assert_eq!(b.len(), n);
        let before_a = a.clone();
        let before_b = b.clone();
        let (output_len, scratch_factor) = match op {
            0 => (2 * n, 12),
            1 | 2 => (n, 12),
            3 => (n, 10),
            _ => panic!("unknown fixture operation {op}"),
        };
        let mut output_guard = guarded(output_len);
        let mut scratch_guard = guarded(scratch_factor * n + extra);
        let right = if op == 2 || shared { &a } else { &b };
        invoke(
            op,
            middle(&mut output_guard),
            &a,
            right,
            middle(&mut scratch_guard),
            threshold,
            top,
        );
        assert_eq!(output_guard[0], CANARY);
        assert_eq!(output_guard[output_len + 1], CANARY);
        assert_eq!(scratch_guard[0], CANARY);
        assert_eq!(scratch_guard[scratch_guard.len() - 1], CANARY);
        assert_eq!(a, before_a, "left input changed in fixture {expected_id}");
        assert_eq!(b, before_b, "right input changed in fixture {expected_id}");
        write!(output, "{}", expected_id).unwrap();
        for word in &output_guard[1..output_len + 1] {
            write!(output, " {}", word).unwrap();
        }
        writeln!(output).unwrap();
    }
    assert_eq!(reader.at, reader.bytes.len());
}

fn assert_rejected<F>(name: &str, call: F, before_output: &[u64], before_scratch: &[u64])
where
    F: FnOnce() -> (Vec<u64>, Vec<u64>),
{
    let result = catch_unwind(AssertUnwindSafe(call));
    let (output, scratch) = result.unwrap_or_else(|_| panic!("invalid wrapper panicked: {name}"));
    assert_eq!(output, before_output, "output changed or invalid case accepted: {name}");
    assert_eq!(scratch, before_scratch, "scratch changed or invalid case accepted: {name}");
}

fn invalid_boundaries() {
    std::panic::set_hook(Box::new(|_| {}));
    let a = vec![1u64, 2];
    let b = vec![3u64, 4];
    let mut output = vec![93u64; 4];
    let mut scratch = vec![94u64; 24];
    let empty: [u64; 0] = [];
    assert_rejected(
        "empty full operands",
        || {
            let result = catch_unwind(AssertUnwindSafe(|| {
                verigmp::toom_multiply::full(&mut [], &[], &[], &mut [], 24)
            }));
            assert!(result.is_err());
            (Vec::new(), Vec::new())
        },
        &empty,
        &empty,
    );
    let before_output = output.clone();
    let before_scratch = scratch.clone();
    assert_rejected(
        "full length mismatch",
        || {
            let result = catch_unwind(AssertUnwindSafe(|| {
                verigmp::toom_multiply::full(&mut output, &a, &b[..1], &mut scratch, 24)
            }));
            assert!(result.is_err());
            (output.clone(), scratch.clone())
        },
        &before_output,
        &before_scratch,
    );
    let before_output = output.clone();
    let before_scratch = scratch.clone();
    assert_rejected(
        "full output short",
        || {
            let result = catch_unwind(AssertUnwindSafe(|| {
                verigmp::toom_multiply::full(&mut output[..3], &a, &b, &mut scratch, 24)
            }));
            assert!(result.is_err());
            (output.clone(), scratch.clone())
        },
        &before_output,
        &before_scratch,
    );
    let before_output = output.clone();
    let before_scratch = scratch.clone();
    assert_rejected(
        "full scratch short",
        || {
            let result = catch_unwind(AssertUnwindSafe(|| {
                verigmp::toom_multiply::full(&mut output, &a, &b, &mut scratch[..23], 24)
            }));
            assert!(result.is_err());
            (output.clone(), scratch.clone())
        },
        &before_output,
        &before_scratch,
    );
    let before_output = output.clone();
    let before_scratch = scratch.clone();
    assert_rejected(
        "threshold below contract",
        || {
            let result = catch_unwind(AssertUnwindSafe(|| {
                verigmp::toom_multiply::full(&mut output, &a, &b, &mut scratch, 23)
            }));
            assert!(result.is_err());
            (output.clone(), scratch.clone())
        },
        &before_output,
        &before_scratch,
    );
    let one = vec![7u64];
    let mut modular_output = vec![95u64; 1];
    let mut modular_scratch = vec![96u64; 12];
    let before_output = modular_output.clone();
    let before_scratch = modular_scratch.clone();
    assert_rejected(
        "modular top zero",
        || {
            let result = catch_unwind(AssertUnwindSafe(|| {
                verigmp::arithmetic::mul_mod(&mut modular_output, &one, &one, &mut modular_scratch, 0)
            }));
            assert!(result.is_err());
            (modular_output.clone(), modular_scratch.clone())
        },
        &before_output,
        &before_scratch,
    );
    let before_output = modular_output.clone();
    let before_scratch = modular_scratch.clone();
    assert_rejected(
        "modular top above word",
        || {
            let result = catch_unwind(AssertUnwindSafe(|| {
                verigmp::arithmetic::mul_mod(&mut modular_output, &one, &one, &mut modular_scratch, 65)
            }));
            assert!(result.is_err());
            (modular_output.clone(), modular_scratch.clone())
        },
        &before_output,
        &before_scratch,
    );
    println!("invalid-boundary-pass cases=7");
}

fn main() {
    let mut args = std::env::args().skip(1);
    match args.next().as_deref() {
        Some("--invalid") => invalid_boundaries(),
        Some(path) if args.next().is_none() => valid_fixture(path),
        _ => panic!("usage: runner --invalid | runner FIXTURE"),
    }
}
