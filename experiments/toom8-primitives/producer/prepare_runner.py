from pathlib import Path
S=Path(__file__).resolve().parent
imports=(S/'candidate/native/lib.rs').read_text()
body=r'''
fn words(s:&str)->Vec<u64>{if s=="-"{vec![]}else{s.split(',').map(|x|x.parse().unwrap()).collect()}}
fn main(){
    use std::io::{self,BufRead,Write};let mut out=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let f:Vec<&str>=line.split('|').collect();assert_eq!(f.len(),7);assert_eq!(f[0],"pair");
        let k:usize=f[1].parse().unwrap();let threshold:usize=f[2].parse().unwrap();assert!(threshold>=24);
        let weights:[u64;8]=words(f[3]).try_into().unwrap();assert!(weights.iter().all(|w|*w<=2097152));assert!(weights.iter().map(|w|*w as u128).sum::<u128>()<4194304);
        let a=words(f[4]);let b=words(f[5]);assert_eq!(a.len(),b.len());assert!(a.len()>=k.checked_mul(7).unwrap() && a.len()<=k.checked_mul(8).unwrap());
        let extra:usize=f[6].parse().unwrap();assert!(extra<=64);let m=k.checked_add(1).unwrap();let n=m.checked_mul(2).unwrap();let work_len=m.checked_mul(14).unwrap().checked_add(extra).unwrap();
        let before_a=a.clone();let before_b=b.clone();
        let mut even=vec![u64::MAX;n+2];let mut odd=vec![0x55aa55aa55aa55aa;n+2];let mut work=vec![0x1122334455667788;work_len+2];
        toom8_producer::weighted_pair(&mut even[1..n+1],&mut odd[1..n+1],&a,&b,k,weights,&mut work[1..work_len+1],threshold);
        assert_eq!(a,before_a);assert_eq!(b,before_b);assert_eq!((even[0],even[n+1]),(u64::MAX,u64::MAX));assert_eq!((odd[0],odd[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));assert_eq!((work[0],work[work_len+1]),(0x1122334455667788,0x1122334455667788));
        writeln!(out,"{}",even[1..n+1].iter().chain(odd[1..n+1].iter()).map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
    }
}
'''
(S/'candidate/native/toom8_producer_runner.rs').write_text(imports+body)
