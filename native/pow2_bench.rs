//! Unverified benchmark driver; all allocation and initialization precede timing.
#[path = "specs/radix.rs"] mod radix;
#[path = "specs/precision.rs"] mod precision;
#[path = "verified/kernel.rs"] mod kernel;
#[path = "verified/limbs.rs"] mod limbs;
#[path = "verified/pow2.rs"] mod pow2;
#[path = "controls/pow2.rs"] mod control;

use std::hint::black_box;
use std::time::Instant;

fn batch<const VERIFIED: bool>(dst: &mut [u64], rhs: &[u64], top: u32, iterations: u64) -> u128 {
    let start = Instant::now();
    for _ in 0..iterations {
        if VERIFIED {
            pow2::add_mod_assign(black_box(&mut *dst), black_box(rhs), black_box(top));
        } else {
            control::add_mod_assign(black_box(&mut *dst), black_box(rhs), black_box(top));
        }
    }
    start.elapsed().as_nanos()
}

fn main() {
    let seed: u64 = std::env::args().nth(1).expect("runtime seed").parse().unwrap();
    println!("limbs,top,repetition,iterations,verified_ns,ordinary_ns");
    for (n, top) in [(1usize,1u32),(1,63),(1,64),(2,1),(2,63),(2,64),
                     (16,7),(256,31),(1024,63),(4096,1),(4096,64)] {
        let rhs: Vec<u64> = (0..n).map(|i| seed.wrapping_mul(i as u64 + 1).rotate_left(23)).collect();
        let initial: Vec<u64> = (0..n).map(|i| seed.wrapping_add(i as u64).rotate_left(37)).collect();
        let mut verified = initial.clone();
        let mut ordinary = initial.clone();
        let mut iterations = 1u64;
        loop {
            let elapsed = batch::<true>(&mut verified, &rhs, top, iterations);
            if elapsed >= 30_000_000 || iterations >= (1 << 30) { break; }
            iterations *= 2;
        }
        for repetition in 0..7 {
            verified.copy_from_slice(&initial);
            ordinary.copy_from_slice(&initial);
            let (v, o) = if repetition % 2 == 0 {
                (batch::<true>(&mut verified, &rhs, top, iterations), batch::<false>(&mut ordinary, &rhs, top, iterations))
            } else {
                let o = batch::<false>(&mut ordinary, &rhs, top, iterations);
                (batch::<true>(&mut verified, &rhs, top, iterations), o)
            };
            assert_eq!(verified, ordinary);
            println!("{n},{top},{repetition},{iterations},{v},{o}");
        }
    }
}
