//! Benchmark-only driver. The `check` command does not read a clock.
use std::{env, fs, hint::black_box, time::Instant};
use verigmp::{arithmetic, fast_multiply, square};

#[link(name = "gmp")]
unsafe extern "C" {
    fn __gmpn_mul_n(out: *mut u64, a: *const u64, b: *const u64, n: isize);
    fn __gmpn_sqr(out: *mut u64, a: *const u64, n: isize);
}

fn apply(op: &str, dst: &mut [u64], a: &[u64], b: &[u64], work: &mut [u64], top: u32) {
    match op {
        "mul_full24" => fast_multiply::full(dst, a, b, work, black_box(24)),
        "mul_full192" => fast_multiply::full(dst, a, b, work, black_box(192)),
        "square_full24" => square::full(dst, a, work, black_box(24)),
        "square_full192" => square::full(dst, a, work, black_box(192)),
        "mul_mod" => arithmetic::mul_mod(dst, a, b, work, top),
        "square_mod" => arithmetic::square_mod(dst, a, work, top),
        _ => panic!("unknown operation"),
    }
}

fn reference(op: &str, a: &[u64], b: &[u64], top: u32) -> Vec<u64> {
    let n = a.len();
    let mut full = vec![0; 2 * n];
    unsafe {
        if op.starts_with("square_") {
            __gmpn_sqr(full.as_mut_ptr(), a.as_ptr(), n as isize);
        } else {
            __gmpn_mul_n(full.as_mut_ptr(), a.as_ptr(), b.as_ptr(), n as isize);
        }
    }
    if op.ends_with("_mod") {
        full.truncate(n);
        if top < 64 { full[n - 1] &= (1u64 << top) - 1; }
    }
    full
}

fn main() {
    let args: Vec<String> = env::args().collect();
    assert_eq!(args.len(), 8, "mode op n top input alias count");
    let mode = &args[1];
    assert!(mode == "check" || mode == "sample" || mode == "calibrate");
    let op = args[2].as_str();
    let n: usize = args[3].parse().unwrap();
    let top: u32 = args[4].parse().unwrap();
    assert!(n > 0 && (1..=64).contains(&top));
    let bytes = fs::read(&args[5]).unwrap();
    assert_eq!(bytes.len(), 16 * n);
    let words: Vec<u64> = bytes.chunks_exact(8)
        .map(|v| u64::from_le_bytes(v.try_into().unwrap())).collect();
    let a = &words[..n];
    let alias: bool = args[6].parse().unwrap();
    let b = if alias {
        assert_eq!(a, &words[n..]);
        a
    } else { &words[n..] };
    let count: u64 = args[7].parse().unwrap();
    let full = op.contains("_full");
    assert!(!full || top == 64);
    let out_len = if full { 2 * n } else { n };
    let scratch_len = match op {
        "mul_full24" | "mul_full192" | "square_full24" | "square_full192" => 3 * n,
        "mul_mod" => 12 * n,
        "square_mod" => 10 * n,
        _ => panic!("unknown operation"),
    };
    let mut out = vec![u64::MAX; out_len];
    let mut work = vec![u64::MAX; scratch_len];
    let expected = reference(op, a, b, top);
    let status = fs::read_to_string("/proc/self/status").unwrap();
    let cpu_list = status.lines().find_map(|line| line.strip_prefix("Cpus_allowed_list:\t")).unwrap();
    apply(op, &mut out, a, b, &mut work, top);
    assert_eq!(out, expected, "GMP comparison before measurement");
    if mode == "check" {
        assert_eq!(count, 0);
        println!("{{\"verified\":true,\"n\":{n},\"top\":{top},\"cpus_allowed\":\"{cpu_list}\"}}");
        return;
    }
    assert!(count > 0);
    let mut iterations = count;
    let mut calibration = Vec::new();
    let elapsed = loop {
        let start = Instant::now();
        for _ in 0..iterations {
            apply(black_box(op), black_box(&mut out), black_box(a), black_box(b),
                black_box(&mut work), black_box(top));
            black_box(&out);
        }
        let ns = start.elapsed().as_nanos();
        calibration.push((iterations, ns));
        assert_eq!(out, expected, "GMP comparison after measurement");
        if mode == "sample" || ns >= 20_000_000 { break ns; }
        iterations = iterations.checked_mul(2).unwrap();
    };
    let history = calibration.iter().map(|(i,t)| format!("[{i},{t}]")).collect::<Vec<_>>().join(",");
    println!("{{\"verified\":true,\"iterations\":{iterations},\"ns\":{elapsed},\"cpus_allowed\":\"{cpu_list}\",\"calibration\":[{history}]}}");
}
