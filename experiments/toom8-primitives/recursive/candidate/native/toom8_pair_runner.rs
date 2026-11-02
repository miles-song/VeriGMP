#[path="specs/radix.rs"] mod radix;
#[path="specs/product.rs"] mod product;
#[path="specs/precision.rs"] mod precision;
#[path="specs/fast_product.rs"] mod fast_product;
#[path="verified/kernel.rs"] mod kernel;
#[path="verified/limbs.rs"] mod limbs;
#[path="verified/pow2.rs"] mod pow2;
#[path="verified/multiply.rs"] mod multiply;
#[path="verified/fast_words.rs"] mod fast_words;
#[path="verified/toom_words.rs"] mod toom_words;
#[path="specs/odd_division.rs"] mod odd_division_spec;
#[path="verified/odd_division.rs"] mod odd_division;
#[path="specs/toom8_pair.rs"] mod toom8_pair_spec;
#[path="verified/toom8_pair.rs"] mod toom8_pair;

fn words(s:&str)->Vec<u64>{if s=="-"{vec![]}else{s.split(',').map(|x|x.parse().unwrap()).collect()}}
fn main(){
    use std::io::{self,BufRead,Write};let mut out=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let f:Vec<&str>=line.split('|').collect();assert_eq!(f.len(),4);assert!(f[0]=="pair"||f[0]=="half");
        let negative=match f[1]{"0"=>false,"1"=>true,_=>panic!("invalid sign")};let a=words(f[2]);let b=words(f[3]);assert_eq!(a.len(),b.len());
        assert!(a.iter().rev().cmp(b.iter().rev())!=std::cmp::Ordering::Less);
        let mut carry=0u128;for (x,y) in a.iter().zip(b.iter()){carry=((*x as u128)+(*y as u128)+carry)>>64;}assert_eq!(carry,0);
        if f[0]=="half"{assert_eq!(a.first().copied().unwrap_or(0)%2,b.first().copied().unwrap_or(0)%2);}
        let n=a.len();let mut plus=vec![u64::MAX;n.checked_add(2).unwrap()];let mut minus=vec![0x55aa55aa55aa55aa;n+2];plus[1..n+1].copy_from_slice(&a);minus[1..n+1].copy_from_slice(&b);
        if f[0]=="pair"{toom8_pair::sum_difference(&mut plus[1..n+1],&mut minus[1..n+1],negative);}
        else{toom8_pair::half_pair(&mut plus[1..n+1],&mut minus[1..n+1],negative);}
        assert_eq!((plus[0],plus[n+1]),(u64::MAX,u64::MAX));assert_eq!((minus[0],minus[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));
        writeln!(out,"{}",plus[1..n+1].iter().chain(minus[1..n+1].iter()).map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
    }
}
