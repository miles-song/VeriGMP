//! Unverified benchmark. The timed operation includes output initialization.
#[path = "specs/radix.rs"] mod radix;
#[path = "specs/precision.rs"] mod precision;
#[path = "specs/product.rs"] mod product;
#[path = "verified/kernel.rs"] mod kernel;
#[path = "verified/limbs.rs"] mod limbs;
#[path = "verified/pow2.rs"] mod pow2;
#[path = "verified/multiply.rs"] mod multiply;
#[path = "controls/multiply.rs"] mod control;
use std::hint::black_box;
use std::time::Instant;

fn batch<const VERIFIED: bool>(out: &mut [u64], a: &[u64], b: &[u64], top: u32, count: u64) -> u128 {
    let start = Instant::now();
    for _ in 0..count {
        if VERIFIED { multiply::mul_mod(black_box(&mut *out),black_box(a),black_box(b),black_box(top)); }
        else { control::mul_mod(black_box(&mut *out),black_box(a),black_box(b),black_box(top)); }
        black_box(&*out);
    }
    start.elapsed().as_nanos()
}

fn main() {
    let seed: u64 = std::env::args().nth(1).expect("runtime seed").parse().unwrap();
    println!("limbs,top,repetition,iterations,verified_ns,ordinary_ns");
    for (n,top) in [(1usize,63u32),(1,64),(2,1),(2,63),(2,64),(4,63),(8,63),
                    (16,63),(32,63),(64,63),(128,63),(256,63),(512,63),(1024,63)] {
        let a: Vec<u64> = (0..n).map(|i| seed.wrapping_mul(i as u64+1).rotate_left(23)).collect();
        let b: Vec<u64> = (0..n).map(|i| seed.wrapping_add(i as u64).rotate_left(37)).collect();
        let mut verified = vec![u64::MAX;n];
        let mut ordinary = vec![u64::MAX;n];
        let mut iterations = 1;
        loop {
            let elapsed = batch::<true>(&mut verified,&a,&b,top,iterations);
            if elapsed >= 30_000_000 || iterations >= (1<<30) { break; }
            iterations *= 2;
        }
        for repetition in 0..7 {
            let (v,o) = if repetition % 2 == 0 {
                (batch::<true>(&mut verified,&a,&b,top,iterations),batch::<false>(&mut ordinary,&a,&b,top,iterations))
            } else {
                let o = batch::<false>(&mut ordinary,&a,&b,top,iterations);
                (batch::<true>(&mut verified,&a,&b,top,iterations),o)
            };
            assert_eq!(verified,ordinary);
            println!("{n},{top},{repetition},{iterations},{v},{o}");
        }
    }
}
