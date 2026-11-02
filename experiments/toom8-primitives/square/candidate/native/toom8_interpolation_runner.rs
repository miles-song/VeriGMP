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

fn words(s:&str)->Vec<u64>{if s=="-"{vec![]}else{s.split(',').map(|x|x.parse().unwrap()).collect()}}
fn main(){
    use std::io::{self,BufRead,Write};let mut out=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let f:Vec<&str>=line.split('|').collect();assert_eq!(f.len(),6);assert_eq!(f[0],"interpolate");
        let k:usize=f[1].parse().unwrap();let threshold:usize=f[2].parse().unwrap();assert!(threshold>=24);
        let a=words(f[3]);let b=words(f[4]);assert_eq!(a.len(),b.len());assert!(a.len()>=k.checked_mul(7).unwrap() && a.len()<=k.checked_mul(8).unwrap());
        let extra:usize=f[5].parse().unwrap();assert!(extra<=64);let m=k.checked_add(1).unwrap();let n=m.checked_mul(2).unwrap();let h=a.len()-7*k;let work_len=m.checked_mul(14).unwrap().checked_add(extra).unwrap();
        let before_a=a.clone();let before_b=b.clone();let mut work=vec![0x1122334455667788;work_len+2];
        let mut low=vec![0x55aa55aa55aa55aa;2*k+2];let mut high=vec![0x55aa55aa55aa55aa;2*h+2];
        let mut e0=vec![0x55aa55aa55aa55aa;n+2];
        let mut e1=vec![0x55aa55aa55aa55aa;n+2];
        let mut e2=vec![0x55aa55aa55aa55aa;n+2];
        let mut e3=vec![0x55aa55aa55aa55aa;n+2];
        let mut e4=vec![0x55aa55aa55aa55aa;n+2];
        let mut e5=vec![0x55aa55aa55aa55aa;n+2];
        let mut o0=vec![0x55aa55aa55aa55aa;n+2];
        let mut o1=vec![0x55aa55aa55aa55aa;n+2];
        let mut o2=vec![0x55aa55aa55aa55aa;n+2];
        let mut o3=vec![0x55aa55aa55aa55aa;n+2];
        let mut o4=vec![0x55aa55aa55aa55aa;n+2];
        let mut o5=vec![0x55aa55aa55aa55aa;n+2];
        let mut o6=vec![0x55aa55aa55aa55aa;n+2];
        toom8_interpolation::interpolate(&mut e0[1..n+1],&mut e1[1..n+1],&mut e2[1..n+1],&mut e3[1..n+1],&mut e4[1..n+1],&mut e5[1..n+1],&mut o0[1..n+1],&mut o1[1..n+1],&mut o2[1..n+1],&mut o3[1..n+1],&mut o4[1..n+1],&mut o5[1..n+1],&mut o6[1..n+1],&mut low[1..2*k+1],&mut high[1..2*h+1],&a,&b,k,&mut work[1..work_len+1],threshold);
        assert_eq!(a,before_a);assert_eq!(b,before_b);assert_eq!((work[0],work[work_len+1]),(0x1122334455667788,0x1122334455667788));
        assert_eq!((low[0],low[2*k+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));assert_eq!((high[0],high[2*h+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((e0[0],e0[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((e1[0],e1[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((e2[0],e2[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((e3[0],e3[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((e4[0],e4[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((e5[0],e5[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((o0[0],o0[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((o1[0],o1[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((o2[0],o2[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((o3[0],o3[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((o4[0],o4[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((o5[0],o5[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        assert_eq!((o6[0],o6[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        let mut result=Vec::new();result.extend_from_slice(&low[1..2*k+1]);
        result.extend_from_slice(&e0[1..n+1]);
        result.extend_from_slice(&e1[1..n+1]);
        result.extend_from_slice(&e2[1..n+1]);
        result.extend_from_slice(&e3[1..n+1]);
        result.extend_from_slice(&e4[1..n+1]);
        result.extend_from_slice(&e5[1..n+1]);
        result.extend_from_slice(&o0[1..n+1]);
        result.extend_from_slice(&o1[1..n+1]);
        result.extend_from_slice(&o2[1..n+1]);
        result.extend_from_slice(&o3[1..n+1]);
        result.extend_from_slice(&o4[1..n+1]);
        result.extend_from_slice(&o5[1..n+1]);
        result.extend_from_slice(&o6[1..n+1]);
        result.extend_from_slice(&high[1..2*h+1]);
        writeln!(out,"{}",result.iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
    }
}
