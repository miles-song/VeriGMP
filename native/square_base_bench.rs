#[path="specs/radix.rs"] mod radix;
#[path="specs/precision.rs"] mod precision;
#[path="specs/product.rs"] mod product;
#[path="specs/fast_product.rs"] mod fast_product;
#[path="specs/toom.rs"] mod toom;
#[path="specs/toom_blocks.rs"] mod toom_blocks;
#[path="specs/square.rs"] mod square_spec;
#[path="verified/kernel.rs"] mod kernel;
#[path="verified/limbs.rs"] mod limbs;
#[path="verified/pow2.rs"] mod pow2;
#[path="verified/multiply.rs"] mod multiply;
#[path="verified/fast_words.rs"] mod fast_words;
#[path="verified/fixed_row.rs"] mod fixed_row;
#[path="verified/toom_words.rs"] mod toom_words;
#[path="verified/toom_evaluate.rs"] mod toom_evaluate;
#[path="verified/toom_interpolate.rs"] mod toom_interpolate;
#[path="verified/fast_multiply.rs"] mod fast_multiply;
#[path="verified/toom_multiply.rs"] mod toom_multiply;
#[path="verified/toom_low.rs"] mod toom_low;
#[path="verified/square.rs"] mod square;
#[path="verified/toom_square.rs"] mod toom_square;
#[path="verified/square_low.rs"] mod square_low;
#[path="verified/mac4.rs"] mod mac4;
#[path="verified/arithmetic.rs"] mod arithmetic;


#[path="specs/square_base.rs"] mod square_base_spec;
#[path="verified/square_base.rs"] mod square_base;

use std::hint::black_box;
use std::time::Instant;
#[link(name="gmp")] extern "C" {fn __gmpn_sqr(out:*mut u64,a:*const u64,n:isize);}
fn run(mode:u32,out:&mut[u64],a:&[u64]) {
    match mode {
        0=>fast_multiply::base_full(out,a,a),
        1=>square_base::full(out,a),
        2=>unsafe{__gmpn_sqr(out.as_mut_ptr(),a.as_ptr(),a.len() as isize)},
        _=>panic!("mode"),
    }
}
fn batch(mode:u32,out:&mut[u64],a:&[u64],count:u64)->u128 {
    let start=Instant::now();
    for _ in 0..count {run(black_box(mode),black_box(&mut *out),black_box(a));black_box(&*out);}
    start.elapsed().as_nanos()
}
fn main() {
    println!("limbs,mode,repetition,iterations,ns");
    for n in [1,2,4,5,6,7,8,9,10,12,15,16,17,23,24,25,32,48,64,128,256] {
        let mut state=20261101u64^(n as u64);
        let a:Vec<u64>=(0..n).map(|_|{state^=state<<13;state^=state>>7;state^=state<<17;state}).collect();
        let mut out=vec![u64::MAX;2*n];let mut expected=out.clone();run(2,&mut expected,&a);
        let mut counts=[1u64;3];
        for m in 0..3 {run(m,&mut out,&a);assert_eq!(out,expected);
            while batch(m,&mut out,&a,counts[m as usize])<10_000_000 {counts[m as usize]*=2;}}
        for rep in 0..7 {for j in 0..3 {let m=(j+rep)%3;let mut count=counts[m as usize];
            let mut elapsed=batch(m,&mut out,&a,count);
            while elapsed<10_000_000 {
                count=count.checked_mul(2).expect("benchmark iteration capacity");
                elapsed=batch(m,&mut out,&a,count);
            }
            counts[m as usize]=count;assert_eq!(out,expected);
            println!("{n},{m},{rep},{count},{elapsed}");}}
    }
}
