#[path="specs/radix.rs"] mod radix;
#[path="specs/fast_product.rs"] mod fast_product;
#[path="verified/kernel.rs"] mod kernel;
#[path="specs/signed_evaluation.rs"] mod signed_evaluation_spec;
#[path="verified/signed_evaluation.rs"] mod signed_evaluation;
#[path="specs/toom8_evaluation.rs"] mod toom8_evaluation_spec;
#[path="verified/toom8_evaluation.rs"] mod toom8_evaluation;

fn words(text:&str)->Vec<u64> {if text=="-"{vec![]}else{text.split(',').map(|v|v.parse().unwrap()).collect()}}
fn boolean(text:&str)->bool {match text{"0"=>false,"1"=>true,_=>panic!("invalid boolean")}}
fn weights(text:&str)->[u64;8] {
    let a:[u64;8]=words(text).try_into().unwrap();assert!(a.iter().all(|x|*x<=2097152));
    assert!(a.iter().map(|x|*x as u128).sum::<u128>()<4194304);a
}
fn main(){
    use std::io::{self,BufRead,Write};
    let mut output=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let f:Vec<&str>=line.split('|').collect();
        if f[0]=="limb" {
            assert_eq!(f.len(),5);let carry:i64=f[1].parse().unwrap();assert!((-4194304..=4194304).contains(&carry));
            let negative=boolean(f[2]);let w=weights(f[3]);let x:[u64;8]=words(f[4]).try_into().unwrap();
            let (low,next)=toom8_evaluation::limb(x[0],x[1],x[2],x[3],x[4],x[5],x[6],x[7],w,carry,negative);
            writeln!(output,"{} {}",low,next).unwrap();
        }else if f[0]=="weights" {
            assert_eq!(f.len(),3);let exponent:u32=f[1].parse().unwrap();assert!(exponent<=3);
            let w=toom8_evaluation::dyadic_weights(exponent,boolean(f[2]));
            writeln!(output,"{}",w.iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
        }else if f[0]=="eval" || f[0]=="dyadic" {
            let point=f[0]=="dyadic";let offset=if point{4}else{3};assert_eq!(f.len(),offset+8);
            let exponent=if point{let e:u32=f[1].parse().unwrap();assert!(e<=3);e}else{0};
            let reciprocal=if point{boolean(f[2])}else{false};let negative=boolean(f[if point{3}else{1}]);
            let w=if point{[0u64;8]}else{weights(f[2])};
            let a:Vec<Vec<u64>>=f[offset..].iter().map(|s|words(s)).collect();let before=a.clone();let k=a[0].len();
            assert!(a[..7].iter().all(|x|x.len()==k));assert!(a[7].len()<=k);
            let mut dst=vec![u64::MAX;k.checked_add(3).unwrap()];let mut tmp=vec![0x55aa55aa55aa55aa;k+3];let old_tmp=tmp.clone();
            let neg=if point{toom8_evaluation::dyadic(&mut dst[1..k+2],&mut tmp[1..k+2],&a[0],&a[1],&a[2],&a[3],&a[4],&a[5],&a[6],&a[7],exponent,reciprocal,negative)}
                else{toom8_evaluation::evaluate(&mut dst[1..k+2],&mut tmp[1..k+2],&a[0],&a[1],&a[2],&a[3],&a[4],&a[5],&a[6],&a[7],w,negative)};
            assert_eq!(a,before);assert_eq!(tmp,old_tmp);assert_eq!(dst[0],u64::MAX);assert_eq!(dst[k+2],u64::MAX);
            writeln!(output,"{} {}",u8::from(neg),dst[1..k+2].iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
        }else{panic!("unknown operation");}
    }
}
