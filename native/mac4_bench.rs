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

use std::time::Instant;use std::hint::black_box;
#[link(name="gmp")] extern "C"{fn __gmpn_addmul_1(out:*mut u64,a:*const u64,n:isize,w:u64)->u64;}
fn run(mode:usize,out:&mut[u64],a:&[u64],w:u64)->u64{match mode{0=>multiply::add_mul_word(out,a,w),1=>mac4::add_mul_word(out,a,w),2=>unsafe{__gmpn_addmul_1(out.as_mut_ptr(),a.as_ptr(),a.len() as isize,w)},_=>panic!()}}
fn batch(mode:usize,out:&mut[u64],a:&[u64],count:u64)->u128{out.fill(u64::MAX);let start=Instant::now();for _ in 0..count{black_box(run(black_box(mode),black_box(&mut *out),black_box(a),black_box(0xfedcba9876543210)));}start.elapsed().as_nanos()}
fn main(){println!("limbs,mode,repetition,iterations,ns");for n in [1,2,3,4,5,7,8,12,16,24,32,64,128,256,512]{let a=vec![0xabcdef0123456789;n];let mut expected=vec![u64::MAX;n];let carry=run(0,&mut expected,&a,0xfedcba9876543210);for mode in 1..3{let mut actual=vec![u64::MAX;n];assert_eq!(carry,run(mode,&mut actual,&a,0xfedcba9876543210));assert_eq!(actual,expected);}let mut out=vec![0;n];let mut counts=[1u64;3];for mode in 0..3{while batch(mode,&mut out,&a,counts[mode])<5_000_000{counts[mode]*=2;}}let count=*counts.iter().max().unwrap();let mut final_state=None;for rep in 0..7{for j in 0..3{let mode=(j+rep)%3;let ns=batch(mode,&mut out,&a,count);if let Some(ref expected)=final_state{assert_eq!(&out,expected);}else{final_state=Some(out.clone());}println!("{n},{mode},{rep},{count},{ns}");}}}}

#[path="specs/square_base.rs"] mod square_base_spec;
#[path="verified/square_base.rs"] mod square_base;
