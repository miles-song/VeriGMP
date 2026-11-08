//! Unverified, non-allocating timed calls into the proved library and GMP.
extern crate verigmp;
use std::hint::black_box;
use std::io::{Read, Write};
use std::time::Instant;
use verigmp::{arithmetic, pow2, toom4_candidate, toom4_low, toom4_square_low};

#[link(name = "gmp")]
extern "C" {
    fn __gmpn_mul_n(out: *mut u64, a: *const u64, b: *const u64, n: isize);
    fn __gmpn_sqr(out: *mut u64, a: *const u64, n: isize);
}

const LIMBS: &[usize] = &[
    1, 256, 511, 512, 513, 1023, 1024, 1025, 1536, 2047, 2048, 2049,
    3072, 4095, 4096, 4097,
];

fn shapes() -> Vec<(usize, u32)> {
    let mut result: Vec<_> = LIMBS.iter().map(|&n| (n, 63)).collect();
    for n in [1024, 2048] { for top in [1, 31, 64] { result.push((n, top)); } }
    for top in [1, 64] { result.push((4096, top)); }
    result.sort_unstable();
    result.dedup();
    result
}

fn next(state: &mut u64) -> u64 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    *state
}

fn call(op: u8, mode: u8, out: &mut [u64], a: &[u64], b: &[u64], scratch: &mut [u64], top: u32) {
    match (op, mode) {
        (0, 0) => arithmetic::mul_mod(out, a, b, scratch, top),
        (0, 1) => toom4_candidate::mul_mod(out, a, b, scratch, top),
        (1, 0) => arithmetic::square_mod(out, a, scratch, top),
        (1, 1) => toom4_candidate::square_mod(out, a, scratch, top),
        (0, 3) => toom4_low::modular(out, a, b, scratch, top, 256, 128, 2),
        (1, 3) => {
            assert!((1..=64).contains(&top));
            toom4_square_low::low(out, a, scratch, 256, 64, 1);
            pow2::normalize_top(out, top);
        }
        (0, 2) | (1, 2) => {
            unsafe {
                if op == 0 { __gmpn_mul_n(scratch.as_mut_ptr(), a.as_ptr(), b.as_ptr(), a.len() as isize); }
                else { __gmpn_sqr(scratch.as_mut_ptr(), a.as_ptr(), a.len() as isize); }
            }
            out.copy_from_slice(&scratch[..a.len()]);
            if top < 64 { *out.last_mut().unwrap() &= (1u64 << top) - 1; }
        }
        _ => panic!("invalid operation or mode"),
    }
}

fn timed(op: u8, mode: u8, out: &mut [u64], a: &[u64], b: &[u64], scratch: &mut [u64], top: u32, count: u64) -> u128 {
    let start = Instant::now();
    for _ in 0..count {
        call(black_box(op), black_box(mode), black_box(&mut *out), black_box(a),
             black_box(b), black_box(&mut *scratch), black_box(top));
        black_box(&*out);
    }
    start.elapsed().as_nanos()
}

fn shape(op: u8, n: usize, top: u32, run: Option<u8>) {
    let mut state = 20261109u64 ^ n as u64 ^ ((top as u64) << 32);
    let a: Vec<u64> = (0..n).map(|_| next(&mut state)).collect();
    let b: Vec<u64> = (0..n).map(|_| next(&mut state)).collect();
    let mut out = vec![u64::MAX; n + 2];
    let capacity = if op == 0 { 12 * n } else { 10 * n };
    let mut scratch = vec![u64::MAX; capacity + 2];
    let mut expected = vec![0; n];
    call(op, 2, &mut expected, &a, &b, &mut scratch[1..=capacity], top);
    for mode in 0..4 {
        call(op, mode, &mut out[1..=n], &a, &b, &mut scratch[1..=capacity], top);
        assert_eq!(&out[1..=n], expected.as_slice());
    }
    if let Some(run) = run {
        let mut count = 1u64;
        for mode in 0..4 {
            while timed(op, mode, &mut out[1..=n], &a, &b, &mut scratch[1..=capacity], top, count) < 20_000_000 {
                count = count.checked_mul(2).unwrap();
            }
        }
        for repetition in 0..7 {
            let order = if (repetition + run as usize) % 2 == 0 { [2, 0, 1, 1, 0, 2, 2, 0, 3, 3, 0, 2] }
                        else { [2, 1, 0, 0, 1, 2, 2, 3, 0, 0, 3, 2] };
            for (position, mode) in order.into_iter().enumerate() {
                let elapsed = timed(op, mode, &mut out[1..=n], &a, &b, &mut scratch[1..=capacity], top, count);
                assert!(elapsed >= 10_000_000, "recorded batch below 10 ms");
                assert_eq!(&out[1..=n], expected.as_slice());
                println!("{run},{op},{n},{top},{repetition},{position},{mode},{count},{elapsed}");
            }
        }
    }
    assert_eq!((out[0], out[n + 1], scratch[0], scratch[capacity + 1]),
               (u64::MAX, u64::MAX, u64::MAX, u64::MAX));
}

fn barrier(phase: &str) {
    eprintln!("VERIGMP_CONTROL_{phase}");
    std::io::stderr().flush().unwrap();
    let mut byte = [0];
    std::io::stdin().read_exact(&mut byte).unwrap();
    assert_eq!(byte, [b'G']);
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("--self-test") if args.len() == 2 => {
            for &(n, top) in &[(1, 1), (9, 64), (511, 63), (512, 63), (1023, 1),
                                (1024, 64), (2047, 31), (2048, 63), (2049, 64)] {
                for op in 0..2 { shape(op, n, top, None); }
            }
            println!("self-test pass; 18 operation/shape pairs, no timing");
        }
        Some("--list") if args.len() == 2 => {
            for (n, top) in shapes() { println!("{n},{top}"); }
        }
        Some("--check-inputs") if args.len() == 2 => {
            for (n, top) in shapes() { for op in 0..2 {
                shape(op, n, top, None);
                println!("{op},{n},{top},pass");
            } }
        }
        Some("--run") if args.len() == 3 => {
            let run: u8 = args[2].parse().unwrap();
            assert!(run < 2);
            barrier("READY");
            println!("run,operation,limbs,top,repetition,position,mode,iterations,ns");
            for (n, top) in shapes() { for op in 0..2 { shape(op, n, top, Some(run)); } }
            barrier("DONE");
        }
        Some("--check-loader") if args.len() == 2 => {
            barrier("READY");
            barrier("DONE");
        }
        _ => panic!("expected --self-test, --list, --check-inputs, --check-loader, or --run 0|1"),
    }
}
