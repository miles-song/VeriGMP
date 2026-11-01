//! Unverified in-process benchmark. Allocate before timing, alternate order,
//! use runtime inputs and black_box, and check both implementations agree.
#[path = "specs/radix.rs"]
mod radix;
#[path = "verified/kernel.rs"]
mod kernel;
#[path = "verified/limbs.rs"]
mod limbs;
#[path = "controls/limbs.rs"]
mod control;

use std::hint::black_box;
use std::time::Instant;

fn batch<const VERIFIED: bool>(dst: &mut [u64], rhs: &[u64], repetitions: u64) -> (u128, u64) {
    let start = Instant::now();
    let mut checksum = 0u64;
    for _ in 0..repetitions {
        let carry = if VERIFIED {
            limbs::add_assign(black_box(&mut *dst), black_box(rhs))
        } else {
            control::add_assign(black_box(&mut *dst), black_box(rhs))
        };
        checksum = checksum.wrapping_add(black_box(carry));
    }
    (start.elapsed().as_nanos(), black_box(checksum))
}

fn main() {
    let seed: u64 = std::env::args().nth(1).expect("runtime seed").parse().unwrap();
    println!("limbs,repetition,iterations,verified_ns,ordinary_ns,checksum");
    for n in [1usize, 4, 16, 64, 256, 1024, 4096, 16384] {
        let rhs: Vec<u64> = (0..n).map(|i| seed.wrapping_mul(i as u64 + 1).rotate_left(23)).collect();
        let initial: Vec<u64> = (0..n).map(|i| seed.wrapping_add(i as u64).rotate_left(37)).collect();
        let mut verified = initial.clone();
        let mut ordinary = initial.clone();
        let mut iterations = 1u64;
        // Calibrate a batch to roughly 40 ms; later timings may vary.
        loop {
            let (elapsed, _) = batch::<true>(&mut verified, &rhs, iterations);
            if elapsed >= 40_000_000 || iterations >= (1 << 30) { break; }
            iterations *= 2;
        }
        for repetition in 0..7 {
            verified.copy_from_slice(&initial);
            ordinary.copy_from_slice(&initial);
            let (v, o) = if repetition % 2 == 0 {
                (batch::<true>(&mut verified, &rhs, iterations), batch::<false>(&mut ordinary, &rhs, iterations))
            } else {
                let o = batch::<false>(&mut ordinary, &rhs, iterations);
                (batch::<true>(&mut verified, &rhs, iterations), o)
            };
            assert_eq!(verified, ordinary);
            assert_eq!(v.1, o.1);
            println!("{n},{repetition},{iterations},{},{},{}", v.0, o.0, v.1);
        }
    }
}
