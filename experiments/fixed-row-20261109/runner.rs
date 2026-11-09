//! Ordinary Rust runner. Shared source and call bodies for both native pairs.
mod ordinary;
use std::hint::black_box;
use std::io::{self, BufRead};
use std::time::Instant;

// Independent observational comparator, outside the verified arithmetic core.
#[link(name = "gmp")]
unsafe extern "C" {
    #[link_name = "__gmpn_mul_n"]
    fn gmp_mul_n(dst: *mut u64, a: *const u64, b: *const u64, n: i64);
    #[link_name = "__gmpn_sqr"]
    fn gmp_sqr(dst: *mut u64, a: *const u64, n: i64);
}

fn words(text: &str) -> Vec<u64> {
    if text == "-" { return Vec::new(); }
    text.split(',').map(|w| u64::from_str_radix(w, 16).unwrap()).collect()
}

fn leaf(dst: &mut [u64], a: &[u64], b: &[u64], control: bool) {
    macro_rules! at {
        ($n:literal) => {
            if control { ordinary::full::<$n>(dst, a, b); }
            else {
                #[cfg(has_fixed_row)]
                verigmp::fixed_row::full::<$n>(dst, a, b);
                #[cfg(not(has_fixed_row))]
                panic!("direct API is candidate-only");
            }
        };
    }
    match a.len() {
        15 => at!(15), 20 => at!(20), 22 => at!(22), 23 => at!(23),
        _ => panic!("selected leaf length"),
    }
}

fn product(op: &str, dst: &mut [u64], a: &[u64], b: &[u64], scratch: &mut [u64], top: u32, threshold: usize) {
    match op {
        "mul" => verigmp::arithmetic::mul_mod(dst, a, b, scratch, top),
        "square" => verigmp::arithmetic::square_mod(dst, a, scratch, top),
        "full" => verigmp::toom_multiply::full(dst, a, b, scratch, threshold),
        "forced" => verigmp::fast_multiply::full(dst, a, b, scratch, threshold),
        "base" => verigmp::fast_multiply::base_full(dst, a, b),
        "direct" => leaf(dst, a, b, false),
        "control" => leaf(dst, a, b, true),
        "gmp_mul" | "gmp_square" | "gmp_full" => {
            let n = a.len();
            assert!(n > 0 && n == b.len() && n <= i64::MAX as usize && scratch.len() >= 2 * n);
            if op == "gmp_square" { unsafe { gmp_sqr(scratch.as_mut_ptr(), a.as_ptr(), n as i64); } }
            else { unsafe { gmp_mul_n(scratch.as_mut_ptr(), a.as_ptr(), b.as_ptr(), n as i64); } }
            let q = if op == "gmp_full" { 2 * n } else { n };
            dst.copy_from_slice(&scratch[..q]);
            if q == n && top < 64 { dst[n - 1] &= (1u64 << top) - 1; }
        }
        _ => panic!("operation"),
    }
}

fn is_full(op: &str) -> bool {
    matches!(op, "full" | "forced" | "direct" | "control" | "base" | "gmp_full")
}

fn sample(path: &str, op: &str, count: u64) {
    assert!(count > 0);
    let text = std::fs::read_to_string(path).unwrap();
    let fields: Vec<_> = text.split_whitespace().collect();
    assert_eq!(fields.len(), 4);
    let top: u32 = fields[0].parse().unwrap();
    let threshold: usize = fields[1].parse().unwrap();
    let a = words(fields[2]); let b = words(fields[3]);
    let q = if is_full(op) { 2 * a.len() } else { a.len() };
    let canary = 0xa5a5a5a5a5a5a5a5;
    let mut dst_frame = vec![canary; q + 2];
    let mut scratch_frame = vec![canary; 12 * a.len() + 2];
    let dst = &mut dst_frame[1..q + 1];
    let scratch = &mut scratch_frame[1..12 * a.len() + 1];
    let mut expected = vec![0; q];
    let oracle = if is_full(op) { "gmp_full" } else if op.contains("square") { "gmp_square" } else { "gmp_mul" };
    product(oracle, &mut expected, &a, &b, scratch, top, threshold);
    scratch.fill(canary);
    product(op, dst, &a, &b, scratch, top, threshold);
    assert_eq!(dst, expected);
    for _ in 0..count.min(32) {
        product(black_box(op), black_box(&mut *dst), black_box(&a), black_box(&b), black_box(&mut *scratch), black_box(top), black_box(threshold));
        black_box(&*dst);
    }
    let start = Instant::now();
    for _ in 0..count {
        product(black_box(op), black_box(&mut *dst), black_box(&a), black_box(&b), black_box(&mut *scratch), black_box(top), black_box(threshold));
        black_box(&*dst);
    }
    let ns = start.elapsed().as_nanos();
    assert_eq!(dst, expected);
    let checksum = |words: &[u64]| words.iter().enumerate().fold(0u64, |x, (i, &w)| x ^ w.rotate_left((i % 64) as u32));
    let output_checksum = checksum(dst);
    assert_eq!(dst_frame[0], canary); assert_eq!(dst_frame[q + 1], canary);
    assert_eq!(scratch_frame[0], canary); assert_eq!(scratch_frame[12 * a.len() + 1], canary);
    println!("sample {op} {count} {ns} {} {} {output_checksum}", checksum(&a), checksum(&b));
}

fn invalid(name: &str) {
    let a = [1u64; 15]; let b = [2u64; 15]; let mut dst = [0u64; 30]; let mut scratch = [0u64; 180];
    match name {
        #[cfg(has_fixed_row)]
        "direct_a" => verigmp::fixed_row::full::<15>(&mut dst, &a[..14], &b),
        #[cfg(has_fixed_row)]
        "direct_b" => verigmp::fixed_row::full::<15>(&mut dst, &a, &b[..14]),
        #[cfg(has_fixed_row)]
        "direct_dst" => verigmp::fixed_row::full::<15>(&mut dst[..29], &a, &b),
        #[cfg(has_fixed_row)]
        "direct_zero" => verigmp::fixed_row::full::<0>(&mut [], &[], &[]),
        "forced_a" => verigmp::fast_multiply::full(&mut dst, &a, &b[..14], &mut scratch, 24),
        "forced_zero" => verigmp::fast_multiply::full(&mut [], &[], &[], &mut [], 24),
        "forced_dst" => verigmp::fast_multiply::full(&mut dst[..29], &a, &b, &mut scratch, 24),
        "forced_scratch" => verigmp::fast_multiply::full(&mut dst, &a, &b, &mut scratch[..44], 24),
        "forced_threshold" => verigmp::fast_multiply::full(&mut dst, &a, &b, &mut scratch, 7),
        "mul_a" => verigmp::arithmetic::mul_mod(&mut dst[..15], &a, &b[..14], &mut scratch, 63),
        "mul_dst" => verigmp::arithmetic::mul_mod(&mut dst[..14], &a, &b, &mut scratch, 63),
        "mul_scratch" => verigmp::arithmetic::mul_mod(&mut dst[..15], &a, &b, &mut scratch[..59], 63),
        "mul_top0" => verigmp::arithmetic::mul_mod(&mut dst[..15], &a, &b, &mut scratch, 0),
        "mul_top65" => verigmp::arithmetic::mul_mod(&mut dst[..15], &a, &b, &mut scratch, 65),
        "square_dst" => verigmp::arithmetic::square_mod(&mut dst[..14], &a, &mut scratch, 63),
        "square_scratch" => verigmp::arithmetic::square_mod(&mut dst[..15], &a, &mut scratch[..149], 63),
        "square_top0" => verigmp::arithmetic::square_mod(&mut dst[..15], &a, &mut scratch, 0),
        "square_top65" => verigmp::arithmetic::square_mod(&mut dst[..15], &a, &mut scratch, 65),
        _ => panic!("unknown invalid case"),
    }
    println!("invalid call returned");
}

fn main() {
    let args: Vec<_> = std::env::args().collect();
    if args.get(1).map(String::as_str) == Some("sample") {
        assert_eq!(args.len(), 5); sample(&args[2], &args[3], args[4].parse().unwrap()); return;
    }
    if args.get(1).map(String::as_str) == Some("invalid") {
        assert_eq!(args.len(), 3); invalid(&args[2]); return;
    }
    if args.get(1).map(String::as_str) == Some("workspace") {
        for n in [0, 1, usize::MAX / 12, usize::MAX / 12 + 1, usize::MAX] {
            println!("{n} {:?} {:?}", verigmp::arithmetic::workspace_len(n), verigmp::arithmetic::square_workspace_len(n));
        }
        return;
    }
    assert_eq!(args.len(), 1);
    for line in io::stdin().lock().lines() {
        let line = line.unwrap(); let f: Vec<_> = line.split_whitespace().collect();
        assert_eq!(f.len(), 7);
        let top: u32 = f[2].parse().unwrap(); let threshold: usize = f[3].parse().unwrap();
        let extra: usize = f[4].parse().unwrap(); let a = words(f[5]); let b = words(f[6]);
        let original_a = a.clone(); let original_b = b.clone();
        let n = a.len(); let q = if is_full(f[1]) { 2 * n } else { n };
        let factor = if f[1] == "forced" { 3 } else if f[1] == "square" { 10 } else { 12 };
        let capacity = if matches!(f[1], "direct" | "control" | "base") { 0 } else { factor * n };
        let canary = 0xa5a5a5a5a5a5a5a5;
        let mut dst = vec![canary; q + 2]; let mut scratch = vec![canary; capacity + extra + 2];
        product(f[1], &mut dst[1..q + 1], &a, &b, &mut scratch[1..capacity + 1], top, threshold);
        assert_eq!(dst[0], canary); assert_eq!(dst[q + 1], canary);
        assert_eq!(scratch[0], canary);
        assert!(scratch[capacity + 1..].iter().all(|&x| x == canary));
        assert_eq!(a, original_a); assert_eq!(b, original_b);
        let out = dst[1..q + 1].iter().map(|w| format!("{w:016x}")).collect::<Vec<_>>().join(",");
        println!("{} {out}", f[0]);
    }
}
