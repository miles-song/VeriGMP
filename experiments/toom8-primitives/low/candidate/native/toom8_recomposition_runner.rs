//! Verified arithmetic on caller-owned little-endian u64 slices.
#[path="specs/radix.rs"] pub mod radix;
#[path="specs/precision.rs"] pub mod precision;
#[path="specs/product.rs"] pub mod product;
#[path="specs/fast_product.rs"] pub mod fast_product;
#[path="verified/kernel.rs"] pub mod kernel;
#[path="verified/limbs.rs"] pub mod limbs;
#[path="verified/pow2.rs"] pub mod pow2;
#[path="verified/multiply.rs"] pub mod multiply;
#[path="verified/fast_words.rs"] pub mod fast_words;
#[path="verified/fast_multiply.rs"] pub mod fast_multiply;
#[path="specs/toom.rs"] pub mod toom;
#[path="specs/toom_blocks.rs"] pub mod toom_blocks;
#[path="specs/square.rs"] pub mod square_spec;
#[path="verified/toom_words.rs"] pub mod toom_words;
#[path="verified/toom_evaluate.rs"] pub mod toom_evaluate;
#[path="verified/toom_interpolate.rs"] pub mod toom_interpolate;
#[path="verified/toom_multiply.rs"] pub mod toom_multiply;
#[path="verified/toom_low.rs"] pub mod toom_low;
#[path="verified/square.rs"] pub mod square;
#[path="verified/toom_square.rs"] pub mod toom_square;
#[path="verified/square_low.rs"] pub mod square_low;
#[path="verified/mac4.rs"] pub mod mac4;
#[path="verified/arithmetic.rs"] pub mod arithmetic;

#[path="specs/square_base.rs"] pub mod square_base_spec;
#[path="verified/square_base.rs"] pub mod square_base;
#[path="specs/toom4.rs"] pub mod toom4;
#[path="verified/toom4_interpolate.rs"] pub mod toom4_interpolate;
#[path="verified/toom4_evaluate.rs"] pub mod toom4_evaluate;
#[path="specs/toom4_blocks.rs"] pub mod toom4_blocks;
#[path="verified/toom4_multiply.rs"] pub mod toom4_multiply;
#[path="verified/toom4_square.rs"] pub mod toom4_square;
#[path="verified/toom4_low.rs"] pub mod toom4_low;
#[path="verified/toom4_square_low.rs"] pub mod toom4_square_low;
#[path="verified/toom4_candidate.rs"] pub mod toom4_candidate;

#[path="specs/odd_division.rs"] pub mod odd_division_spec;
#[path="verified/odd_division.rs"] pub mod odd_division;

#[path="verified/scaled_subtraction.rs"] pub mod scaled_subtraction;

#[path="specs/signed_evaluation.rs"] pub mod signed_evaluation_spec;
#[path="verified/signed_evaluation.rs"] pub mod signed_evaluation;

#[path="specs/wide_odd_division.rs"] pub mod wide_odd_division_spec;
#[path="verified/wide_odd_division.rs"] pub mod wide_odd_division;

#[path="specs/toom8_newton.rs"] pub mod toom8_newton_spec;
#[path="verified/toom8_newton.rs"] pub mod toom8_newton;

#[path="specs/toom8_evaluation.rs"] pub mod toom8_evaluation_spec;
#[path="verified/toom8_evaluation.rs"] pub mod toom8_evaluation;

#[path="specs/toom8_pair.rs"] pub mod toom8_pair_spec;
#[path="verified/toom8_pair.rs"] pub mod toom8_pair;

#[path="specs/toom8_producer.rs"] pub mod toom8_producer_spec;
#[path="verified/toom8_producer.rs"] pub mod toom8_producer;

#[path="specs/toom8_convolution.rs"] pub mod toom8_convolution;

#[path="specs/toom8_dyadic_producer.rs"] pub mod toom8_dyadic_producer_spec;
#[path="verified/toom8_dyadic_producer.rs"] pub mod toom8_dyadic_producer;

#[path="specs/toom8_normalization.rs"] pub mod toom8_normalization_spec;
#[path="verified/toom8_normalization.rs"] pub mod toom8_normalization;

#[path="verified/toom8_even.rs"]
pub mod toom8_even;

#[path="specs/toom8_seventh.rs"] pub mod toom8_seventh_spec;
#[path="verified/toom8_seventh.rs"] pub mod toom8_seventh;

#[path="verified/toom8_interpolation.rs"] pub mod toom8_interpolation;

#[path="specs/toom8_recomposition.rs"] pub mod toom8_recomposition_spec;
#[path="verified/toom8_recomposition.rs"] pub mod toom8_recomposition;

fn words(s:&str)->Vec<u64>{if s=="-"{vec![]}else{s.split(',').map(|x|x.parse().unwrap()).collect()}}
fn main(){
    use std::io::{self,BufRead,Write};let mut out=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let f:Vec<&str>=line.split('|').collect();assert_eq!(f.len(),20);assert_eq!(f[0],"recompose");
        let k:usize=f[1].parse().unwrap();let a=words(f[2]);let b=words(f[3]);assert_eq!(a.len(),b.len());assert!(a.len()>=k.checked_mul(7).unwrap() && a.len()<=k.checked_mul(8).unwrap());
        let extra:usize=f[19].parse().unwrap();assert!(extra<=64);let n=a.len().checked_mul(2).unwrap();
        let before_a=a.clone();let before_b=b.clone();let mut dst=vec![0x55aa55aa55aa55aa;n+extra+2];
        let z0=words(f[4]);let before_z0=z0.clone();
        let z1=words(f[5]);let before_z1=z1.clone();
        let z2=words(f[6]);let before_z2=z2.clone();
        let z3=words(f[7]);let before_z3=z3.clone();
        let z4=words(f[8]);let before_z4=z4.clone();
        let z5=words(f[9]);let before_z5=z5.clone();
        let z6=words(f[10]);let before_z6=z6.clone();
        let z7=words(f[11]);let before_z7=z7.clone();
        let z8=words(f[12]);let before_z8=z8.clone();
        let z9=words(f[13]);let before_z9=z9.clone();
        let z10=words(f[14]);let before_z10=z10.clone();
        let z11=words(f[15]);let before_z11=z11.clone();
        let z12=words(f[16]);let before_z12=z12.clone();
        let z13=words(f[17]);let before_z13=z13.clone();
        let z14=words(f[18]);let before_z14=z14.clone();
        toom8_recomposition::assemble_exact(&mut dst[1..n+1],&z0,&z1,&z2,&z3,&z4,&z5,&z6,&z7,&z8,&z9,&z10,&z11,&z12,&z13,&z14,&a,&b,k);
        assert_eq!(a,before_a);assert_eq!(b,before_b);assert_eq!(dst[0],0x55aa55aa55aa55aa);assert!(dst[n+1..].iter().all(|x|*x==0x55aa55aa55aa55aa));
        assert_eq!(z0,before_z0);
        assert_eq!(z1,before_z1);
        assert_eq!(z2,before_z2);
        assert_eq!(z3,before_z3);
        assert_eq!(z4,before_z4);
        assert_eq!(z5,before_z5);
        assert_eq!(z6,before_z6);
        assert_eq!(z7,before_z7);
        assert_eq!(z8,before_z8);
        assert_eq!(z9,before_z9);
        assert_eq!(z10,before_z10);
        assert_eq!(z11,before_z11);
        assert_eq!(z12,before_z12);
        assert_eq!(z13,before_z13);
        assert_eq!(z14,before_z14);
        writeln!(out,"{}",dst[1..n+1].iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
    }
}
