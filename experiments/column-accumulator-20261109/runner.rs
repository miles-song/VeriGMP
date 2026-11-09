//! Oracle/measurement driver; unverified infrastructure, never linked by native/lib.rs.
mod column;

use std::hint::black_box;
use std::io::{self, BufRead};
use std::time::Instant;

fn words(text: &str) -> Vec<u64> {
    text.split(',').map(|word| u64::from_str_radix(word, 16).expect("hex word")).collect()
}

fn product(case: &str, dst: &mut [u64], a: &[u64], b: &[u64]) {
    match case {
        "column" => column::column_prefix(dst, a, b),
        "column_full" => column::column_full(dst, a, b),
        "column_low" => column::column_low(dst, a, b),
        "row_full" => verigmp::fast_multiply::base_full(dst, a, b),
        "row_low" => verigmp::fast_multiply::base_low(dst, a, b),
        _ => panic!("unknown operation"),
    }
}

fn checksum(words: &[u64]) -> u64 {
    words.iter().enumerate().fold(0u64, |sum, (i, &word)| sum ^ word.rotate_left((i % 64) as u32))
}

fn sample(path: &str, case: &str, count: u64) {
    assert!(count > 0);
    let data = std::fs::read(path).expect("input file");
    let text = std::str::from_utf8(&data).expect("UTF-8 input");
    let fields: Vec<_> = text.split_whitespace().collect();
    assert_eq!(fields.len(), 3);
    let q: usize = fields[0].parse().expect("output width");
    let a = words(fields[1]);
    let b = words(fields[2]);
    let mut dst = vec![0xa5a5a5a5a5a5a5a5; q];
    let mut expected = vec![0; q];
    product("column", &mut expected, &a, &b);
    product(case, &mut dst, &a, &b);
    assert_eq!(dst, expected);
    let warmup = count.min(1024);
    for _ in 0..warmup {
        product(black_box(case), black_box(&mut dst), black_box(&a), black_box(&b));
        black_box(&dst);
    }
    let start = Instant::now();
    for _ in 0..count {
        product(black_box(case), black_box(&mut dst), black_box(&a), black_box(&b));
        black_box(&dst);
    }
    let elapsed = start.elapsed().as_nanos();
    assert_eq!(dst, expected);
    println!("sample {case} {count} {elapsed} {}", checksum(&dst));
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.get(1).map(String::as_str) == Some("sample") {
        assert_eq!(args.len(), 5);
        sample(&args[2], &args[3], args[4].parse().expect("positive sample count"));
        return;
    }
    assert_eq!(args.len(), 1);
    for line in io::stdin().lock().lines() {
        let line = line.expect("input line");
        let fields: Vec<_> = line.split_whitespace().collect();
        assert_eq!(fields.len(), 5);
        let q: usize = fields[2].parse().expect("output width");
        assert!((1..=256).contains(&q));
        let a = words(fields[3]);
        let b = words(fields[4]);
        let original_a = a.clone();
        let original_b = b.clone();
        let mut storage = vec![0xa5a5a5a5a5a5a5a5; q + 2];
        let dst = &mut storage[1..q + 1];
        product(fields[1], dst, &a, &b);
        let output = dst.iter().map(|word| format!("{word:016x}")).collect::<Vec<_>>().join(",");
        assert_eq!(storage[0], 0xa5a5a5a5a5a5a5a5);
        assert_eq!(storage[q + 1], 0xa5a5a5a5a5a5a5a5);
        assert_eq!(a, original_a);
        assert_eq!(b, original_b);
        println!("{} {}", fields[0], output);
    }
}
