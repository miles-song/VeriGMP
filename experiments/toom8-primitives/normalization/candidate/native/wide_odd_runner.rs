#[path="specs/radix.rs"] mod radix;
#[path="specs/wide_odd_division.rs"] mod wide_odd_division_spec;
#[path="verified/wide_odd_division.rs"] mod wide_odd_division;

fn supported(d:u64)->bool { matches!(d,3|15|63|255|1023|4095) }
fn inverse_ok(d:u64,inv:u64) {
    assert!(d>0);
    assert_eq!((d as u128)*(inv as u128)%(1u128<<64),1);
}
fn exact(words:&[u64],d:u64) {
    assert!(d>0);let mut remainder=0u128;
    for word in words.iter().rev() {remainder=((remainder<<64)|(*word as u128))%(d as u128);}
    assert_eq!(remainder,0);
}
fn main(){
    use std::io::{self,BufRead,Write};
    let mut output=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let mut fields=line.split_whitespace();
        let op=fields.next().unwrap();let a:Vec<u64>=fields.map(|s|s.parse().unwrap()).collect();
        let answer=if op=="limb" {
            assert_eq!(a.len(),4);inverse_ok(a[0],a[1]);assert!(a[2]<a[0]);
            let (q,carry)=wide_odd_division::quotient_limb(a[3],a[2],a[0],a[1]);vec![q,carry]
        }else if op=="inverse" {
            assert_eq!(a.len(),1);assert!(supported(a[0]));vec![wide_odd_division::toom8_inverse(a[0])]
        }else if op=="exact" || op=="family" {
            let offset=if op=="exact"{3}else{2};assert!(a.len()>=offset);
            let d=a[0];let n=usize::try_from(a[offset-1]).unwrap();
            assert_eq!(a.len(),offset.checked_add(n).unwrap());let original=&a[offset..];
            let inv=if op=="exact"{inverse_ok(d,a[1]);a[1]}else{assert!(supported(d));wide_odd_division::toom8_inverse(d)};
            exact(original,d);
            let mut out=vec![u64::MAX;n.checked_add(2).unwrap()];out[1..n+1].copy_from_slice(original);
            if op=="exact" {wide_odd_division::divide_exact_with_inverse(&mut out[1..n+1],d,inv);}
            else {wide_odd_division::divide_toom8_odd(&mut out[1..n+1],d);}
            assert_eq!((out[0],out[n+1]),(u64::MAX,u64::MAX));out[1..n+1].to_vec()
        }else {panic!("unknown operation")};
        for (i,value) in answer.iter().enumerate(){if i>0{write!(output," ").unwrap();}write!(output,"{}",value).unwrap();}
        writeln!(output).unwrap();
    }
}
